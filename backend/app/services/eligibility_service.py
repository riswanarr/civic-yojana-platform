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


class EligibilityService:
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

    def get_eligibility(
        self,
        access_token: str,
        scheme_id: str,
    ) -> dict[str, Any]:
        user_id = self._get_authenticated_user_id(
            access_token
        )

        profile = self._fetch_profile(user_id)
        scheme = self._fetch_scheme(scheme_id)

        return self._generate_eligibility(
            profile,
            scheme,
        )

    def _get_authenticated_user_id(
        self,
        access_token: str,
    ) -> str:
        print("TOKEN START:", access_token[:30])
        print("SUPABASE URL:", settings.supabase_url)

        try:
            response = self.supabase_client.auth.get_user(
                access_token
            )
            print("AUTH RESPONSE:", response)

        except Exception as exc:
            print("AUTH ERROR:", repr(exc))
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
                detail="Profile not found.",
            )

        return response.data[0]

    def _fetch_scheme(
        self,
        scheme_id: str,
    ) -> dict[str, Any]:
        response = (
            self.supabase_client.table("schemes")
            .select("*")
            .eq("id", scheme_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheme not found.",
            )

        return response.data[0]

    def _generate_eligibility(
        self,
        profile: dict[str, Any],
        scheme: dict[str, Any],
    ) -> dict[str, Any]:
        score = 50
        matched = []

        if (
            profile.get("state")
            and scheme.get("state")
            and profile["state"] == scheme["state"]
        ):
            score += 20
            matched.append("State matches")

        if profile.get("education_level"):
            score += 15
            matched.append("Education information available")

        if profile.get("occupation"):
            score += 15
            matched.append("Occupation information available")

        return {
            "scheme_id": scheme["id"],
            "scheme_title": scheme["title"],
            "eligibility_score": min(score, 100),
            "status": (
                "Highly Eligible"
                if score >= 80
                else "Possibly Eligible"
            ),
            "matched_criteria": matched,
            "missing_requirements": [],
            "reason": (
                f"You appear to match several "
                f"criteria for {scheme['title']}."
            ),
        }


eligibility_service = EligibilityService()



