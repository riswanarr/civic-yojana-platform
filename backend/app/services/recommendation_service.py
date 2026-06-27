import json
import re
from typing import Any

from fastapi import HTTPException, status
from supabase import create_client

from app.config import settings


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

        recommendations = self._rank_with_gemini(
            profile,
            schemes,
        )

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

        for scheme in schemes:
            score = 50
            reasons = []

            title = (
                scheme.get("title", "")
                or ""
            ).lower()

            description = (
                scheme.get("description", "")
                or ""
            ).lower()

            eligibility = (
                scheme.get("eligibility_criteria", "")
                or ""
            ).lower()

            text = (
                f"{title} "
                f"{description} "
                f"{eligibility}"
            )

            if (
                str(
                    profile.get(
                        "occupation",
                        "",
                    )
                ).lower()
                == "student"
            ):
                if any(
                    word in text
                    for word in [
                        "student",
                        "scholarship",
                        "education",
                        "internship",
                    ]
                ):
                    score += 25
                    reasons.append(
                        "matches your student profile"
                    )

            if (
                str(
                    profile.get(
                        "state",
                        "",
                    )
                ).lower()
                == "kerala"
                and "kerala" in text
            ):
                score += 20
                reasons.append(
                    "is available in Kerala"
                )

            if (
                str(
                    profile.get(
                        "gender",
                        "",
                    )
                ).lower()
                == "female"
            ):
                if any(
                    word in text
                    for word in [
                        "girl",
                        "female",
                        "women",
                    ]
                ):
                    score += 15
                    reasons.append(
                        "supports female beneficiaries"
                    )

            score = min(score, 100)

            if reasons:
                reason = (
                    "Recommended because it "
                    + ", ".join(reasons)
                    + "."
                )
            else:
                reason = (
                    "Recommended based on your profile."
                )

            recommendations.append(
                {
                    "scheme_id": scheme["id"],
                    "title": scheme["title"],
                    "score": score,
                    "reason": reason,
                }
            )

        recommendations.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return recommendations[:5]

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