import json
import logging
import re
from typing import Any

from fastapi import HTTPException, status
from supabase import create_client

from app.config import settings
from app.services.eligibility_service import eligibility_service
from app.services.notification_service import notification_service


PROFILE_FIELDS = [
    "state",
    "age",
    "gender",
    "education_level",
    "occupation",
    "annual_family_income",
    "category",
    "disability_status",
    "minority_status",
]

SCHEME_FIELDS = [
    "id",
    "title",
    "description",
    "category",
    "eligibility_criteria",
    "benefits",
    "state",
    "deadline",
]


logger = logging.getLogger(__name__)

EXPLANATION_CRITERIA = [
    "state matches",
    "available across india",
    "occupation matches",
    "education matches",
    "gender requirement matches",
    "category matches",
    "disability status matches",
    "minority status matches",
]


class RecommendationService:
    def __init__(self) -> None:
        self._supabase_client = None

    @property
    def supabase_client(self):
        if self._supabase_client is None:
            supabase_key = (
                settings.supabase_service_role_key
                or settings.supabase_anon_key
            )

            if not settings.supabase_url or not supabase_key:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Supabase configuration is missing.",
                )

            self._supabase_client = create_client(
                settings.supabase_url,
                supabase_key,
            )

        return self._supabase_client

    def get_recommendations(
        self,
        access_token: str,
    ) -> dict[str, list[dict[str, Any]]]:
        user_id = self._get_authenticated_user_id(access_token)
        profile = self._fetch_profile(user_id)
        schemes = self._fetch_schemes()

        if not schemes:
            return {"recommendations": []}

        recommendations = self._generate_fallback_recommendations(
            profile,
            schemes,
        )
        try:
            notification_service.create_from_recommendations(user_id, recommendations)
        except Exception:
            logger.exception("Unable to create recommendation notifications.")

        return {"recommendations": recommendations[:5]}

    def _get_authenticated_user_id(
        self,
        access_token: str,
    ) -> str:
        try:
            response = self.supabase_client.auth.get_user(
                access_token
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
            ) from exc

        user = getattr(response, "user", None)
        user_id = getattr(user, "id", None)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user could not be identified.",
            )

        return str(user_id)

    def _fetch_profile(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        response = (
            self.supabase_client.table("profiles")
            .select(",".join(PROFILE_FIELDS))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found.",
            )

        return response.data[0]

    def _fetch_schemes(self) -> list[dict[str, Any]]:
        response = (
            self.supabase_client.table("schemes")
            .select(",".join(SCHEME_FIELDS))
            .execute()
        )

        return response.data or []

    def _rank_with_gemini(
        self,
        profile: dict[str, Any],
        schemes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.gemini_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gemini API key is missing.",
            )

        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
        )

        prompt = self._build_prompt(profile, schemes)

        try:
            response = model.invoke(prompt)
            content = (
                response.content
                if isinstance(response.content, str)
                else json.dumps(response.content)
            )

            return self._parse_recommendations(content)

        except HTTPException:
            raise

        except Exception as exc:
            print("GEMINI ERROR:", repr(exc))
            return self._generate_fallback_recommendations(
                profile,
                schemes,
            )

    def _generate_fallback_recommendations(
        self,
        profile: dict[str, Any],
        schemes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        recommendations = []
        seen_keys = set()

        for scheme in schemes:
            try:
                eligibility = eligibility_service._generate_eligibility(profile, scheme)
            except Exception:
                logger.exception("Unable to score scheme for recommendations.")
                continue

            scheme_type = eligibility.get("scheme_type", "Grant")
            relevance = self._scheme_type_relevance(profile, scheme_type)
            score = min(97, max(0, eligibility["eligibility_score"] + relevance))
            scheme_id = str(scheme.get("id") or "").strip()
            title = eligibility.get("scheme_title") or scheme.get("title") or "Untitled Scheme"
            equivalent_key = self._equivalent_key(title, scheme_type)

            if not scheme_id or score < 50 or relevance <= -20 or not eligibility.get("hard_restrictions_passed", True):
                continue

            if eligibility.get("additional_verification_required"):
                score = min(score, 69)

            if equivalent_key in seen_keys:
                continue

            reasons = self._filter_explanation_reasons(eligibility["matched_criteria"])[:4]
            if not reasons:
                continue

            reason = self._build_recommendation_reason(
                reasons,
                scheme_type,
                eligibility.get("missing_requirements", []),
            )
            seen_keys.add(equivalent_key)

            recommendations.append(
                {
                    "scheme_id": scheme_id,
                    "title": title,
                    "score": score,
                    "reason": reason,
                    "scheme_type": scheme_type,
                    "deadline": eligibility["deadline"],
                    "hard_restrictions_passed": eligibility.get("hard_restrictions_passed", True),
                    "additional_verification_required": eligibility.get("additional_verification_required", False),
                    "equivalent_key": equivalent_key,
                }
            )

        recommendations.sort(
            key=lambda item: (item["score"], self._type_rank(profile, item["scheme_type"])),
            reverse=True,
        )

        return recommendations[:5]

    def _scheme_type_relevance(
        self,
        profile: dict[str, Any],
        scheme_type: str,
    ) -> int:
        occupation = eligibility_service._normalize_occupation(profile.get("occupation"))

        if occupation == "student":
            return {
                "Scholarship": 10,
                "Internship": 9,
                "Grant": 5,
                "Training": 3,
                "Fellowship": 0,
                "Entrepreneurship": -8,
                "Job": -25,
                "Portal": -30,
                "Service": -30,
                "Resource": -30,
            }.get(scheme_type, 0)

        if occupation == "job_seeker":
            return {
                "Job": 16,
                "Training": 15,
                "Internship": 12,
                "Fellowship": 0,
                "Entrepreneurship": -2,
                "Grant": -6,
                "Scholarship": -25,
                "Portal": -30,
                "Service": -30,
                "Resource": -30,
            }.get(scheme_type, 0)

        if occupation == "employed":
            return {
                "Fellowship": 10,
                "Training": 9,
                "Entrepreneurship": 8,
                "Grant": 2,
                "Job": 0,
                "Internship": -10,
                "Scholarship": -25,
                "Portal": -30,
                "Service": -30,
                "Resource": -30,
            }.get(scheme_type, 0)

        if occupation in {"self_employed", "entrepreneur", "business_owner"}:
            return {
                "Entrepreneurship": 12,
                "Grant": 8,
                "Training": 5,
                "Fellowship": 0,
                "Scholarship": -15,
                "Internship": -15,
                "Job": -20,
                "Portal": -30,
                "Service": -30,
                "Resource": -30,
            }.get(scheme_type, 0)

        return 0

    def _type_rank(self, profile: dict[str, Any], scheme_type: str) -> int:
        return self._scheme_type_relevance(profile, scheme_type)

    def _filter_explanation_reasons(self, reasons: list[str]) -> list[str]:
        filtered = []
        for reason in reasons:
            normalized = reason.lower()
            if any(criterion in normalized for criterion in EXPLANATION_CRITERIA):
                filtered.append(reason)
        return filtered

    def _equivalent_key(self, title: Any, scheme_type: str) -> str:
        clean_title = eligibility_service._clean_title(title)
        normalized_title = re.sub(r"[^a-z0-9]+", " ", clean_title.lower()).strip()
        return f"{scheme_type.lower()}:{normalized_title}"

    def _build_recommendation_reason(
        self,
        reasons: list[str],
        scheme_type: str,
        missing_requirements: list[str] | None = None,
    ) -> str:
        lowered = [reason.lower() for reason in reasons if reason]
        if len(lowered) == 1:
            details = lowered[0]
        else:
            details = ", ".join(lowered[:-1]) + f", and {lowered[-1]}"

        verification_notes = [
            requirement
            for requirement in missing_requirements or []
            if "requires verification" in requirement.lower()
        ]
        suffix = f" {verification_notes[0]}" if verification_notes else ""

        return f"Recommended because {details}, and your profile aligns with this {scheme_type.lower()}.{suffix}"

    def _build_prompt(
        self,
        profile: dict[str, Any],
        schemes: list[dict[str, Any]],
    ) -> str:
        payload = {
            "user_profile": profile,
            "schemes": schemes,
        }

        return (
            "Analyze the user's eligibility and relevance for the listed "
            "government schemes. Rank the schemes and return only the top 5 "
            "recommendations. Each recommendation must include scheme_id, "
            "title, score from 0 to 100, and reason in 1-2 sentences. "
            "Return valid JSON only with this exact shape: "
            '{"recommendations":[{"scheme_id":"...","title":"...",'
            '"score":95,"reason":"..."}]}. '
            f"Input JSON: {json.dumps(payload, ensure_ascii=False)}"
        )

    def _parse_recommendations(
        self,
        content: str,
    ) -> list[dict[str, Any]]:
        parsed = self._load_json(content)

        raw_recommendations = (
            parsed.get("recommendations", [])
            if isinstance(parsed, dict)
            else []
        )

        recommendations: list[dict[str, Any]] = []

        for item in raw_recommendations:
            if not isinstance(item, dict):
                continue

            scheme_id = str(
                item.get("scheme_id", "")
            ).strip()

            title = str(
                item.get("title", "")
            ).strip()

            reason = str(
                item.get("reason", "")
            ).strip()

            try:
                score = int(item.get("score", 0))
            except (TypeError, ValueError):
                score = 0

            if scheme_id and title and reason:
                recommendations.append(
                    {
                        "scheme_id": scheme_id,
                        "title": title,
                        "score": max(0, min(score, 100)),
                        "reason": reason,
                    }
                )

        return recommendations

    def _load_json(self, content: str) -> Any:
        cleaned = content.strip()

        fenced_match = re.search(
            r"```(?:json)?\s*(.*?)\s*```",
            cleaned,
            re.DOTALL,
        )

        if fenced_match:
            cleaned = fenced_match.group(1).strip()

        return json.loads(cleaned)


recommendation_service = RecommendationService()
