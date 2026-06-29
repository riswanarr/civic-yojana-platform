from app.services.eligibility_service import EligibilityService
from app.services.notification_service import NotificationService
from app.services.recommendation_service import RecommendationService
from app.services.update_service import PARSER_REGISTRY, UpdateService


def profile(**overrides):
    data = {
        "state": "Kerala",
        "age": 22,
        "gender": "Male",
        "education_level": "Undergraduate Engineering",
        "occupation": "Student",
        "annual_family_income": 300000,
        "category": "General",
        "disability_status": "No",
        "minority_status": "No",
    }
    data.update(overrides)
    return data


def scheme(**overrides):
    data = {
        "id": "scheme-1",
        "title": "Kerala Student Scholarship",
        "category": "Scholarship",
        "state": "Kerala",
        "eligibility_criteria": "Scholarship for undergraduate students with family income below 8 lakh.",
    }
    data.update(overrides)
    return data


def score(profile_data, scheme_data):
    return EligibilityService()._generate_eligibility(profile_data, scheme_data)


def test_student_profile_scores_well_for_scholarship_scheme():
    result = score(profile(), scheme())

    assert result["eligibility_score"] >= 75
    assert result["status"] in {"Strong Match", "Near Perfect Match"}
    assert "Occupation matches student scholarship focus" in result["matched_criteria"]
    assert "Income criteria satisfied" in result["matched_criteria"]


def test_engineering_student_scores_well_for_aicte_student_scheme():
    result = score(
        profile(gender="Female"),
        scheme(
            title="AICTE Pragati Scholarship for Girls",
            state="All India",
            eligibility_criteria="Scholarship for female engineering students with income below 8 lakh.",
        ),
    )

    assert result["eligibility_score"] >= 80
    assert result["status"] in {"Strong Match", "Near Perfect Match"}
    assert "Education matches scholarship focus" in result["matched_criteria"]
    assert "Gender requirement matches" in result["matched_criteria"]


def test_job_seeker_prefers_job_scheme_over_scholarship():
    service = RecommendationService()
    recommendations = service._generate_fallback_recommendations(
        profile(occupation="Job Seeker", education_level="Graduate"),
        [
            scheme(id="scholarship", title="Student Scholarship", category="Scholarship"),
            scheme(
                id="job",
                title="Kerala Government Job Recruitment",
                category="Government Job",
                eligibility_criteria="Recruitment vacancy for job seekers above 18.",
            ),
        ],
    )

    assert recommendations[0]["scheme_id"] == "job"
    assert all(item["scheme_id"] != "scholarship" for item in recommendations[:1])


def test_occupation_variants_normalize_to_job_seeker():
    service = EligibilityService()

    for occupation in ["Job Seeker", "job seeker", "jobseeker", "JobSeeker", "Seeking Employment"]:
        assert service._normalize_occupation(occupation) == "job_seeker"


def test_sc_job_seeker_prioritizes_jobs_over_category_matched_scholarships():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(occupation="JobSeeker", education_level="Graduate", category="SC"),
        [
            scheme(
                id="sc-scholarship",
                title="SC Student Scholarship",
                category="Scholarship",
                eligibility_criteria="Scholarship for SC students with income below 8 lakh.",
            ),
            scheme(
                id="sc-job",
                title="SC Government Recruitment Drive",
                category="Government Job",
                eligibility_criteria="Recruitment vacancy for SC candidates above 18.",
            ),
            scheme(
                id="training",
                title="Skill Development Training for Job Seekers",
                category="Training",
                state="All India",
                eligibility_criteria="Training scheme for job seekers.",
            ),
        ],
    )

    assert recommendations[0]["scheme_id"] == "sc-job"
    assert "sc-scholarship" not in [item["scheme_id"] for item in recommendations[:2]]


def test_general_job_seeker_scores_common_job_schemes_realistically():
    for title in ["Jobseeker", "Find Domestic Jobs", "Find International Jobs"]:
        result = score(
            profile(occupation="Seeking Employment", education_level="Graduate", category="General"),
            scheme(
                title=title,
                category="Government Job",
                state="All India",
                eligibility_criteria="Employment opportunity for job seekers.",
            ),
        )

        assert result["eligibility_score"] >= 60
        assert any("Occupation matches" in item for item in result["matched_criteria"])


def test_student_normalization_preserves_scholarship_priority():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(occupation="student"),
        [
            scheme(id="job", title="Find Domestic Jobs", category="Government Job", state="All India"),
            scheme(id="scholarship", title="Student Merit Scholarship", category="Scholarship", state="All India"),
        ],
    )

    assert recommendations[0]["scheme_id"] == "scholarship"


def test_employed_normalization_preserves_training_priority():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(occupation="employed", education_level="Graduate"),
        [
            scheme(id="training", title="Professional Upskilling Training", category="Training", state="All India"),
            scheme(id="scholarship", title="Student Merit Scholarship", category="Scholarship", state="All India"),
        ],
    )

    assert recommendations[0]["scheme_id"] == "training"


def test_female_profile_matches_women_scheme():
    result = score(
        profile(gender="Female", occupation="Self Employed"),
        scheme(
            title="Women Entrepreneurship Support Scheme",
            category="Subsidy",
            eligibility_criteria="Support scheme for women entrepreneurs.",
        ),
    )

    assert result["eligibility_score"] >= 60
    assert "Gender requirement matches" in result["matched_criteria"]


def test_obc_profile_matches_category_scheme():
    result = score(
        profile(category="OBC"),
        scheme(
            title="OBC Post Matric Scholarship",
            eligibility_criteria="Scholarship for OBC students with income below 8 lakh.",
        ),
    )

    assert result["eligibility_score"] >= 80
    assert "OBC category matches" in result["matched_criteria"]


def test_state_specific_scheme_penalizes_wrong_state():
    result = score(
        profile(state="Tamil Nadu"),
        scheme(state="Kerala"),
    )

    assert result["eligibility_score"] < 50
    assert "Available only in Kerala" in result["missing_requirements"]


def test_student_profile_matches_internship_scheme():
    result = score(
        profile(),
        scheme(
            title="Engineering Internship Programme",
            category="Internship",
            state="All India",
            eligibility_criteria="Internship for engineering students.",
        ),
    )

    assert result["eligibility_score"] >= 50
    assert "Occupation matches internship focus" in result["matched_criteria"]


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeNotificationsTable:
    def __init__(self, existing):
        self.rows = list(existing)
        self.inserted = []
        self._pending_insert = None
        self._filters = {}

    def select(self, fields):
        self._pending_insert = None
        self._filters = {}
        return self

    def eq(self, field, value):
        self._filters[field] = value
        return self

    def in_(self, field, values):
        self._filters[field] = set(values)
        return self

    def limit(self, count):
        return self

    def insert(self, rows):
        self._pending_insert = rows
        return self

    def execute(self):
        if self._pending_insert is not None:
            self.inserted = list(self._pending_insert)
            self.rows.extend(self.inserted)
            self._pending_insert = None
            return FakeResponse(self.inserted)

        results = []
        for row in self.rows:
            matched = True
            for field, value in self._filters.items():
                if isinstance(value, set):
                    matched = row.get(field) in value
                else:
                    matched = row.get(field) == value
                if not matched:
                    break
            if matched:
                results.append(row)

        return FakeResponse(results)


class FakeNotificationClient:
    def __init__(self, existing=None):
        self.table_instance = FakeNotificationsTable(existing or [])

    def table(self, name):
        return self.table_instance


def test_notification_generation_uses_recommendation_threshold_and_prevents_duplicates():
    service = NotificationService()
    service._client = FakeNotificationClient(
        existing=[
            {
                "user_id": "user-1",
                "scheme_id": "duplicate",
                "title": "Strong scheme match available",
            }
        ]
    )

    created = service.create_from_recommendations(
        "user-1",
        [
            {"scheme_id": "duplicate", "title": "Duplicate", "score": 95, "scheme_type": "Scholarship"},
            {"scheme_id": "strong", "title": "Strong Match", "score": 82, "scheme_type": "Scholarship"},
            {"scheme_id": "weak", "title": "Weak Match", "score": 69, "scheme_type": "Scholarship"},
        ],
    )

    assert created == 1
    assert service._client.table_instance.inserted[0]["scheme_id"] == "strong"


def test_recommendation_notifications_are_idempotent_across_dashboard_refreshes():
    service = NotificationService()
    service._client = FakeNotificationClient()
    recommendations = [
        {
            "scheme_id": "strong",
            "title": "Strong Match",
            "score": 82,
            "scheme_type": "Scholarship",
            "hard_restrictions_passed": True,
        }
    ]

    first_created = service.create_from_recommendations("user-1", recommendations)
    second_created = service.create_from_recommendations("user-1", recommendations)

    assert first_created == 1
    assert second_created == 0
    assert len(service._client.table_instance.rows) == 1


def test_notification_generation_after_job_seeker_occupation_normalization():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(occupation="JobSeeker", education_level="Graduate"),
        [
            scheme(
                id="domestic-jobs",
                title="Find Domestic Jobs",
                category="Government Job",
                state="All India",
                eligibility_criteria="Employment opportunity for job seekers.",
            )
        ],
    )

    service = NotificationService()
    service._client = FakeNotificationClient()

    created = service.create_from_recommendations("user-1", recommendations)

    assert created == 1
    assert service._client.table_instance.inserted[0]["scheme_id"] == "domestic-jobs"


def test_sync_notifications_are_idempotent_when_sync_runs_twice():
    service = UpdateService()
    service._client = FakeNotificationClient()
    service._client.table_instance.rows = [{"user_id": "user-1"}]
    opportunity = {"id": "scheme-1", "title": "Live Scheme"}

    first_created = service.create_notifications([opportunity])
    second_created = service.create_notifications([opportunity])

    notification_rows = [
        row
        for row in service._client.table_instance.rows
        if row.get("title") == "New opportunity available"
    ]

    assert first_created == 1
    assert second_created == 0
    assert len(notification_rows) == 1


def test_notification_generation_returns_empty_when_deleted_or_low_score_items_are_not_recommended():
    service = NotificationService()
    service._client = FakeNotificationClient()

    created = service.create_from_recommendations(
        "user-1",
        [{"scheme_id": "deleted-low", "title": "Deleted Low", "score": 40, "scheme_type": "Job"}],
    )

    assert created == 0
    assert service._client.table_instance.inserted == []


def test_category_group_treats_sc_st_obc_as_alternatives():
    result = score(
        profile(category="OBC"),
        scheme(
            title="Post Matric Scholarship for SC/ST/OBC Students",
            eligibility_criteria="Available for SC/ST/OBC students with income below 8 lakh.",
        ),
    )

    assert "OBC category matches" in result["matched_criteria"]
    assert "SC category required" not in result["missing_requirements"]
    assert "ST category required" not in result["missing_requirements"]


def test_missing_mandatory_category_caps_score():
    result = score(
        profile(category="General"),
        scheme(
            title="SC Student Scholarship",
            eligibility_criteria="Scholarship for SC students with income below 8 lakh.",
        ),
    )

    assert result["eligibility_score"] < 50
    assert "SC category required" in result["missing_requirements"]
    assert result["status"] == "Low Match"


def test_scheme_type_detection_distinguishes_common_opportunities():
    service = EligibilityService()

    assert service._infer_scheme_type(scheme(title="Digital India Internship Scheme")) == "Internship"
    assert service._infer_scheme_type(scheme(title="ISRO Scientist Recruitment", category="Government Job")) == "Job"
    assert service._infer_scheme_type(scheme(title="Pragati Scholarship")) == "Scholarship"
    assert service._infer_scheme_type(scheme(title="Skill Development Training Programme")) == "Training"
    assert service._infer_scheme_type(scheme(title="Startup India Seed Grant")) == "Grant"


def test_student_recommendations_prioritize_scholarships_and_internships_over_jobs():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(),
        [
            scheme(id="job", title="ISRO Scientist Recruitment", category="Government Job"),
            scheme(id="internship", title="Digital India Internship Scheme", category="Internship", state="All India"),
            scheme(id="scholarship", title="Pragati Scholarship", category="Scholarship", state="All India"),
        ],
    )

    assert [item["scheme_id"] for item in recommendations[:2]] == ["scholarship", "internship"]
    assert all("job" != item["scheme_id"] for item in recommendations[:2])


def test_employed_profile_prioritizes_training_and_entrepreneurship():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(occupation="Employed", education_level="Graduate"),
        [
            scheme(id="scholarship", title="Student Scholarship", category="Scholarship"),
            scheme(id="training", title="Advanced Upskilling Training Programme", category="Training", state="All India"),
            scheme(
                id="startup",
                title="Entrepreneurship Support Scheme",
                category="Grant",
                state="All India",
                eligibility_criteria="Grant for entrepreneurs and business owners.",
            ),
        ],
    )

    assert recommendations[0]["scheme_id"] in {"training", "startup"}
    assert all(item["scheme_id"] != "scholarship" for item in recommendations)


def test_minority_profile_matches_minority_scheme():
    result = score(
        profile(minority_status="Yes"),
        scheme(
            title="Minority Merit Scholarship",
            eligibility_criteria="Scholarship for minority students with income below 8 lakh.",
        ),
    )

    assert "Minority status matches" in result["matched_criteria"]
    assert result["eligibility_score"] >= 75


def test_disability_profile_matches_disability_scheme():
    result = score(
        profile(disability_status="Yes"),
        scheme(
            title="Scholarship for Students with Disabilities",
            eligibility_criteria="Scholarship for students with disability and income below 8 lakh.",
        ),
    )

    assert "Disability status matches" in result["matched_criteria"]
    assert result["eligibility_score"] >= 75


def test_recommendation_explanation_only_uses_matched_criteria():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(category="OBC"),
        [
            scheme(
                id="obc-scholarship",
                title="Scholarship for SC/ST/OBC Students",
                eligibility_criteria="Available for SC/ST/OBC students with income below 8 lakh.",
            )
        ],
    )

    reason = recommendations[0]["reason"]

    assert "obc category matches" in reason
    assert "sc category matches" not in reason
    assert "st category matches" not in reason


def test_deadline_fallback_is_user_friendly():
    result = score(profile(), scheme(deadline=None))

    assert result["deadline"] == "Check official website for latest deadline."


def test_notifications_skip_untyped_or_low_confidence_recommendations():
    service = NotificationService()
    service._client = FakeNotificationClient()

    created = service.create_from_recommendations(
        "user-1",
        [
            {"scheme_id": "untyped", "title": "Untyped", "score": 95},
            {
                "scheme_id": "uncertain",
                "title": "Uncertain",
                "score": 85,
                "scheme_type": "Grant",
                "reason": "Eligibility is uncertain.",
            },
        ],
    )

    assert created == 0
    assert service._client.table_instance.inserted == []


def test_minority_only_scheme_is_filtered_for_non_minority_user():
    result = score(
        profile(minority_status="No"),
        scheme(
            title="Minority Merit Scholarship",
            eligibility_criteria="Scholarship for minority students with income below 8 lakh.",
        ),
    )

    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(minority_status="No"),
        [
            scheme(
                id="minority-scholarship",
                title="Minority Merit Scholarship",
                eligibility_criteria="Scholarship for minority students with income below 8 lakh.",
            )
        ],
    )

    assert result["eligibility_score"] < 50
    assert result["hard_restrictions_passed"] is False
    assert recommendations == []


def test_single_girl_child_requires_additional_verification_without_profile_field():
    profile_data = profile(gender="Female")
    scheme_data = scheme(
        id="single-girl-child",
        title="Single Girl Child Scholarship",
        eligibility_criteria="Scholarship for single girl child students with income below 8 lakh.",
    )
    result = score(
        profile_data,
        scheme_data,
    )
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile_data,
        [scheme_data],
    )

    assert result["eligibility_score"] <= 74
    assert result["status"] == "Possible Match"
    assert "Single girl child status requires verification." in result["missing_requirements"]
    assert recommendations[0]["score"] < 70
    assert "Single girl child status requires verification." in recommendations[0]["reason"]

    service = NotificationService()
    service._client = FakeNotificationClient()

    assert service.create_from_recommendations("user-1", recommendations) == 0


def test_explicit_single_girl_child_confirmation_allows_high_confidence_notification():
    profile_data = profile(gender="Female", single_girl_child=True)
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile_data,
        [
            scheme(
                id="single-girl-child",
                title="Single Girl Child Scholarship",
                eligibility_criteria="Scholarship for single girl child students with income below 8 lakh.",
            )
        ],
    )

    service = NotificationService()
    service._client = FakeNotificationClient()

    assert recommendations[0]["score"] >= 70
    assert recommendations[0]["additional_verification_required"] is False
    assert service.create_from_recommendations("user-1", recommendations) == 1


def test_ambiguous_income_values_are_normalized_without_crashing():
    result = score(
        profile(annual_family_income=5),
        scheme(eligibility_criteria="Scholarship for students with family income below 8 lakh."),
    )

    assert result["eligibility_score"] >= 75
    assert "Income criteria satisfied" in result["matched_criteria"]


def test_undergraduate_profile_is_mismatch_for_school_stage_schemes():
    profile_data = profile(age=19, education_level="Undergraduate", occupation="Student")
    scheme_data = scheme(
        id="nmms-like",
        title="National Means-cum-Merit Scholarship",
        eligibility_criteria=(
            "Scholarship for regular school students entering class IX after selection "
            "at class VIII with family income below 3.5 lakh."
        ),
    )
    result = score(profile_data, scheme_data)
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile_data,
        [scheme_data],
    )

    assert result["eligibility_score"] < 50
    assert "Education-stage mismatch: scheme targets school-stage students." in result["missing_requirements"]
    assert recommendations == []


def test_informational_pages_are_classified_as_portal_service_or_resource():
    service = EligibilityService()

    assert service._infer_scheme_type(scheme(title="Schemes", category="Information")) == "Resource"
    assert service._infer_scheme_type(scheme(title="Application Status", category="Service")) == "Service"
    assert service._infer_scheme_type(scheme(title="Scholarship Eligibility", category="Information")) == "Resource"
    assert service._infer_scheme_type(scheme(title="Jobseeker", category="Service")) == "Service"
    assert service._infer_scheme_type(scheme(title="Find Career Center", category="Service")) == "Service"


def test_title_tagline_is_removed_from_recommendation_title():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(),
        [
            scheme(
                id="internship-portal",
                title="AICTE Internship Portal Your dream internship is just a click away",
                category="Internship",
                state="All India",
                eligibility_criteria="Internship for engineering students.",
            )
        ],
    )

    assert recommendations[0]["title"] == "AICTE Internship Portal"


def test_duplicate_equivalent_recommendations_are_removed():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(),
        [
            scheme(id="first", title="Pragati Scholarship", category="Scholarship", state="All India"),
            scheme(id="second", title="Pragati Scholarship Your gateway to education support", category="Scholarship", state="All India"),
        ],
    )

    assert len(recommendations) == 1
    assert recommendations[0]["scheme_id"] == "first"


def test_notification_uses_recommendation_score_without_recalculation():
    service = NotificationService()
    service._client = FakeNotificationClient()

    created = service.create_from_recommendations(
        "user-1",
        [
            {
                "scheme_id": "job",
                "title": "Find Domestic Jobs",
                "score": 72,
                "scheme_type": "Job",
                "hard_restrictions_passed": True,
                "equivalent_key": "job:find domestic jobs",
            }
        ],
    )

    assert created == 1
    assert "72% score" in service._client.table_instance.inserted[0]["message"]


def test_notifications_skip_recommendations_that_failed_hard_restrictions():
    service = NotificationService()
    service._client = FakeNotificationClient()

    created = service.create_from_recommendations(
        "user-1",
        [
            {
                "scheme_id": "minority",
                "title": "Minority Scholarship",
                "score": 95,
                "scheme_type": "Scholarship",
                "hard_restrictions_passed": False,
            }
        ],
    )

    assert created == 0
    assert service._client.table_instance.inserted == []


def test_recommendation_explanation_omits_non_allowed_generic_matches():
    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(occupation="Unknown", education_level="Unknown"),
        [scheme(id="resource", title="Startup India Seed Grant", category="Grant", state="All India")],
    )

    assert recommendations == []


def test_recommendation_generation_handles_scoring_exceptions(monkeypatch):
    def raise_error(profile_data, scheme_data):
        raise RuntimeError("scoring failed")

    monkeypatch.setattr(
        "app.services.recommendation_service.eligibility_service._generate_eligibility",
        raise_error,
    )

    recommendations = RecommendationService()._generate_fallback_recommendations(
        profile(),
        [scheme(id="broken", title="Broken Scheme")],
    )

    assert recommendations == []


def test_source_fetch_handles_socket_resource_failures(monkeypatch):
    class FailingParser:
        def fetch(self, source):
            raise OSError("[WinError 10055] no buffer space available")

    monkeypatch.setitem(PARSER_REGISTRY, "failing", FailingParser())

    assert UpdateService().fetch_source({"name": "Failing Source", "parser_name": "failing"}) == []
