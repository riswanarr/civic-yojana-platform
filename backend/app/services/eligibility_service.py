from typing import Any
import re

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

HIGHER_EDUCATION_TERMS = [
    "undergraduate",
    "graduate",
    "postgraduate",
    "post graduate",
    "phd",
    "diploma",
    "btech",
    "engineering",
]

SCHOLARSHIP_TERMS = ["scholarship", "student", "education", "college", "university"]
INTERNSHIP_TERMS = ["internship", "apprentice", "apprenticeship"]
JOB_TERMS = ["job", "recruitment", "vacancy", "employment"]
TRAINING_TERMS = ["training", "skill", "upskilling", "course", "capacity building"]
FELLOWSHIP_TERMS = ["fellowship", "research fellow", "post doctoral"]
GRANT_TERMS = ["grant", "financial assistance", "aid"]
ENTREPRENEURSHIP_TERMS = ["entrepreneur", "startup", "self employment", "business", "msme"]
WOMEN_TERMS = ["women", "woman", "female", "girl"]
CATEGORY_TERMS = ["obc", "sc", "st", "ews"]
PORTAL_TERMS = ["portal", "dashboard"]
SERVICE_TERMS = ["service", "application status", "career center", "career centre"]
RESOURCE_TERMS = ["schemes", "resources", "guidelines", "information", "directory"]
DEADLINE_FALLBACK = "Check official website for latest deadline."


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
        score = 0
        matched = []
        missing = []
        score_caps = [100]
        additional_verification_required = False

        text = self._scheme_text(scheme)
        criteria = ((scheme.get("eligibility_criteria") or "").lower())
        scheme_type = self._infer_scheme_type(scheme)
        clean_title = self._clean_title(scheme.get("title"))

        profile_state = (profile.get("state") or "").lower()
        scheme_state = (scheme.get("state") or "").lower()
        profile_gender = (profile.get("gender") or "").lower()
        profile_category = (profile.get("category") or "").lower()
        education = (profile.get("education_level") or "").lower()
        occupation = self._normalize_occupation(profile.get("occupation"))
        disability_status = str(profile.get("disability_status") or "").lower()
        minority_status = str(profile.get("minority_status") or "").lower()
        age = profile.get("age") or 0
        income = self._normalize_income(profile.get("annual_family_income"))

        requires_state = scheme_state and scheme_state != "all india"
        state_matches = False

        if requires_state:
            if profile_state == scheme_state:
                score += 25
                state_matches = True
                matched.append(f"{scheme['state']} state matches")
            else:
                missing.append(f"Available only in {scheme['state']}")
                score_caps.append(45)
        elif scheme_state == "all india":
            score += 5
            state_matches = True
            matched.append("Available across India")

        is_higher_education = any(term in education for term in HIGHER_EDUCATION_TERMS)
        is_student = occupation == "student" or (not occupation and is_higher_education)
        school_stage_mismatch = self._has_school_stage_requirement(text) and is_higher_education

        if school_stage_mismatch:
            missing.append("Education-stage mismatch: scheme targets school-stage students.")
            score_caps.append(49)

        if scheme_type in {"Portal", "Service", "Resource"}:
            score += 20
            matched.append(f"{scheme_type} is available for profile review")
            if occupation == "job_seeker" and self._contains_any(text, ["job", "career", "employment"]):
                score += 40
                matched.append("Occupation matches employment service focus")

        if scheme_type == "Scholarship":
            if is_student:
                score += 34
                matched.append("Occupation matches student scholarship focus")
                if is_higher_education:
                    score += 12
                    matched.append("Education matches scholarship focus")
            else:
                missing.append("Student status appears required")
                score_caps.append(55)

        if scheme_type == "Internship":
            if occupation == "student" or is_higher_education:
                score += 36
                matched.append("Occupation matches internship focus")
                if is_higher_education:
                    score += 10
                    matched.append("Education matches internship focus")
            elif occupation == "job_seeker":
                score += 34
                matched.append("Occupation matches apprenticeship or internship focus")
            elif occupation == "employed":
                score += 14
                matched.append("Occupation may match internship or apprenticeship focus")
            else:
                missing.append("Student or early-career status may be required")
                score_caps.append(60)

        if scheme_type == "Job":
            if occupation in {"job_seeker", "employed"}:
                score += 55
                matched.append("Occupation matches job or recruitment focus")
            elif occupation == "student":
                missing.append("Work-seeking status may be required")
                score_caps.append(55)
            else:
                missing.append("Job seeker or employed status may be required")
                score_caps.append(55)

        if scheme_type == "Training":
            if occupation == "job_seeker":
                score += 42
                matched.append("Occupation matches training or skill development focus")
            elif occupation in {"employed", "student"}:
                score += 32
                matched.append("Occupation matches training or skill development focus")
            else:
                missing.append("Training audience needs manual verification")

        if scheme_type == "Fellowship":
            if occupation == "employed" or is_higher_education:
                score += 28
                matched.append("Education matches fellowship focus")
            else:
                missing.append("Advanced academic or professional profile may be required")
                score_caps.append(60)

        if scheme_type == "Grant":
            score += 16
            matched.append("Resource provides financial support for profile review")

        if scheme_type == "Entrepreneurship Scheme":
            if occupation in {"employed", "self_employed", "entrepreneur", "business_owner"}:
                score += 30
                matched.append("Occupation matches entrepreneurship focus")
            else:
                missing.append("Entrepreneurship or self-employment profile may be required")
                score_caps.append(65)

        if self._contains_any(text, WOMEN_TERMS):
            if profile_gender == "female":
                score += 35
                matched.append("Gender requirement matches")
            else:
                missing.append("Scheme appears intended for women")
                score_caps.append(49)

        detected_categories = self._detect_category_groups(text)
        if detected_categories:
            if profile_category in detected_categories:
                score += 28
                matched.append(f"{profile_category.upper()} category matches")
            else:
                required = "/".join(category.upper() for category in detected_categories)
                missing.append(f"{required} category required")
                score_caps.append(49)

        if "above 18" in criteria:
            if age >= 18:
                score += 15
                matched.append("Age requirement matches")
            else:
                missing.append("Must be above 18 years")
                score_caps.append(49)

        if "income" in criteria or "family income" in criteria:
            income_limit = self._extract_income_limit(criteria)
            if income_limit and income and income <= income_limit:
                score += 20
                matched.append("Income criteria satisfied")
            elif income_limit and income:
                missing.append("Family income appears above scheme limit")
                score_caps.append(60)
            else:
                missing.append("Income limit needs manual verification")
                score_caps.append(75)

        if "disability" in text or "disabled" in text or "divyang" in text:
            if disability_status in {"yes", "true", "disabled", "person with disability"}:
                score += 36
                matched.append("Disability status matches")
            else:
                missing.append("Disability status appears required")
                score_caps.append(49)

        if "minority" in text:
            if self._is_affirmative(minority_status):
                score += 30
                matched.append("Minority status matches")
            else:
                missing.append("Minority status appears required")
                score_caps.append(49)

        if "single girl child" in text or "single-girl-child" in text:
            if profile.get("single_girl_child") is True:
                score += 25
                matched.append("Single girl child status matches")
            else:
                missing.append("Single girl child status requires verification.")
                score_caps.append(74)
                additional_verification_required = True

        if score == 0:
            score = 55 if not missing else 35

        score = min(score, min(score_caps), 97)

        if not matched and not missing:
            missing.append("Detailed eligibility criteria could not be determined automatically.")
        elif not matched:
            missing.append("Profile does not clearly match the detected scheme requirements.")
        elif len(missing) == 0 and score < 80 and scheme_type not in {"Portal", "Service", "Resource"}:
            missing.append("Some detailed criteria may still need manual verification.")

        if score >= 90:
            status = "Near Perfect Match"
        elif score >= 75:
            status = "Strong Match"
        elif score >= 50:
            status = "Possible Match"
        else:
            status = "Low Match"

        return {
            "scheme_id": scheme["id"],
            "scheme_title": clean_title,
            "eligibility_score": score,
            "status": status,
            "matched_criteria": matched,
            "missing_requirements": missing,
            "reason": (
                self._build_reason(matched, missing, scheme_type)
            ),
            "scheme_type": scheme_type,
            "deadline": scheme.get("deadline") or DEADLINE_FALLBACK,
            "hard_restrictions_passed": not self._has_hard_missing_requirement(missing),
            "additional_verification_required": additional_verification_required,
        }

    def _scheme_text(self, scheme: dict[str, Any]) -> str:
        return " ".join(
            str(scheme.get(field) or "")
            for field in ["title", "description", "category", "state", "eligibility_criteria"]
        ).lower()

    def _contains_any(self, text: str, terms: list[str]) -> bool:
        return any(term in text for term in terms)

    def _normalize_occupation(self, occupation: Any) -> str:
        normalized = re.sub(r"[^a-z]", "", str(occupation or "").lower())

        if normalized in {"jobseeker", "seekingemployment", "seekingjob", "unemployed"}:
            return "job_seeker"
        if normalized in {"student", "studying"}:
            return "student"
        if normalized in {"employed", "employee", "working"}:
            return "employed"
        if normalized in {"selfemployed", "selfemployment"}:
            return "self_employed"
        if normalized in {"businessowner"}:
            return "business_owner"
        if normalized in {"entrepreneur"}:
            return "entrepreneur"

        return str(occupation or "").strip().lower().replace(" ", "_")

    def _normalize_income(self, income: Any) -> int:
        if income in {None, ""}:
            return 0

        try:
            value = float(str(income).replace(",", "").strip())
        except (TypeError, ValueError):
            return 0

        if 0 < value <= 100:
            value *= 100000

        return int(value)

    def _is_affirmative(self, value: str) -> bool:
        return value in {"yes", "true", "minority", "disabled", "person with disability"}

    def _infer_scheme_type(self, scheme: dict[str, Any]) -> str:
        text = self._scheme_text(scheme)
        category = str(scheme.get("category") or "").lower()
        title = str(scheme.get("title") or "").lower()
        informational_type = self._infer_informational_type(title)

        if informational_type:
            return informational_type

        if self._contains_any(text, INTERNSHIP_TERMS):
            return "Internship"
        if self._contains_any(text, JOB_TERMS) or "job" in category:
            return "Job"
        if self._contains_any(text, FELLOWSHIP_TERMS):
            return "Fellowship"
        if self._contains_any(text, TRAINING_TERMS):
            return "Training"
        if self._contains_any(text, GRANT_TERMS):
            return "Grant"
        if self._contains_any(text, ENTREPRENEURSHIP_TERMS):
            return "Entrepreneurship"
        if self._contains_any(text, SCHOLARSHIP_TERMS) or "scholarship" in category:
            return "Scholarship"
        if self._contains_any(title, PORTAL_TERMS):
            return "Portal"
        if self._contains_any(title, SERVICE_TERMS):
            return "Service"
        if self._contains_any(title, RESOURCE_TERMS):
            return "Resource"

        return "Resource"

    def _infer_informational_type(self, title: str) -> str | None:
        normalized_title = re.sub(r"[^a-z0-9]+", " ", title).strip()

        if normalized_title in {"schemes", "scholarship eligibility"}:
            return "Resource"
        if normalized_title in {"application status", "jobseeker", "find career center", "find career centre"}:
            return "Service"
        if normalized_title.endswith(" portal"):
            return "Portal"

        return None

    def _detect_category_groups(self, text: str) -> list[str]:
        detected = [
            category
            for category in CATEGORY_TERMS
            if re.search(rf"(?<![a-z0-9]){category}(?![a-z0-9])", text)
        ]
        if not detected:
            return []

        ordered = [category for category in CATEGORY_TERMS if category in detected]
        return ordered

    def _clean_title(self, title: Any) -> str:
        value = " ".join(str(title or "Untitled Scheme").split())
        tagline_markers = [" your ", " - your ", ": your "]
        lowered = value.lower()

        for marker in tagline_markers:
            index = lowered.find(marker)
            if index > 0:
                return value[:index].strip(" -:")

        return value

    def _has_hard_missing_requirement(self, missing: list[str]) -> bool:
        hard_terms = [
            "available only",
            "required",
            "above scheme limit",
            "education-stage mismatch",
            "appears intended for women",
            "appears required",
        ]
        return any(any(term in item.lower() for term in hard_terms) for item in missing)

    def _has_school_stage_requirement(self, text: str) -> bool:
        school_patterns = [
            r"\bclass\s*(?:viii|ix|x|xi|xii|8|9|10|11|12)\b",
            r"\bsecondary stage\b",
            r"\bschool[- ]stage\b",
            r"\bschool students?\b",
            r"\bregular students?.*school\b",
        ]
        return any(re.search(pattern, text) for pattern in school_patterns)

    def _build_reason(
        self,
        matched: list[str],
        missing: list[str],
        scheme_type: str,
    ) -> str:
        if not matched:
            return "Eligibility is uncertain because the profile does not clearly satisfy the detected mandatory criteria."

        if len(matched) == 1:
            match_text = matched[0]
        else:
            match_text = ", ".join(matched[:-1]) + f", and {matched[-1]}"

        if missing:
            return f"{match_text}. Some requirements still need verification for this {scheme_type.lower()}."

        return f"{match_text}. Your profile is a strong fit for this {scheme_type.lower()}."

    def _extract_income_limit(self, criteria: str) -> int | None:
        match = re.search(r"(?:income|family income)[^0-9]*(\d+(?:\.\d+)?)\s*(lakh|lac|lakhs|lacs)?", criteria)
        if not match:
            return None

        amount = float(match.group(1))
        if match.group(2):
            amount *= 100000

        return int(amount)


eligibility_service = EligibilityService()
