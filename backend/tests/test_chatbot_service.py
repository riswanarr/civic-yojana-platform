from types import SimpleNamespace

import numpy as np

from app.services import chatbot_service as chatbot_module
from app.services import web_search_service as web_search_module
from app.services.chatbot_service import (
    DYNAMIC_PORTAL_PLACEHOLDER_RESPONSE,
    DYNAMIC_UNVERIFIED_RESPONSE,
    INSUFFICIENT_RELEVANCE_RESPONSE,
    ChatbotService,
)
from app.services.web_search_service import UNVERIFIED_WEB_RESULT, WebSearchService


class FakeGeminiModel:
    last_prompt = ""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, prompt: str):
        FakeGeminiModel.last_prompt = prompt
        return SimpleNamespace(content="Personalized answer from grounded context.")


def test_personalized_answer_injects_profile_context(monkeypatch):
    service = ChatbotService()
    profile = {
        "age": 22,
        "gender": "Female",
        "state": "Kerala",
        "occupation": "Student",
        "education_level": "Graduate",
        "annual_family_income": 250000,
        "category": "OBC",
        "disability_status": False,
        "minority_status": True,
    }

    monkeypatch.setattr(service, "_get_authenticated_user_id", lambda token: "user-1")
    monkeypatch.setattr(service, "_fetch_profile", lambda user_id: profile)
    monkeypatch.setattr(
        service,
        "retrieve_sources",
        lambda query, limit=5, fetch_k=20, search_type="mmr": [
            {
                "type": "scheme",
                "scheme_id": "scheme-1",
                "title": "Startup Support",
                "category": "Entrepreneurship",
                "state": "Kerala",
                "application_link": "https://startupindia.gov.in",
                "snippet": "Support for students and entrepreneurs.",
            }
        ],
    )
    monkeypatch.setattr(chatbot_module, "ChatGoogleGenerativeAI", FakeGeminiModel)

    response = service.answer_personalized_question(
        "token",
        "What schemes can help me start a business?",
        history=[],
    )

    assert response["answer"] == "Personalized answer from grounded context."
    assert response["used_profile"] is True
    assert response["used_web_search"] is False
    assert "Gender: Female" in FakeGeminiModel.last_prompt
    assert "State: Kerala" in FakeGeminiModel.last_prompt
    assert "Occupation: Student" in FakeGeminiModel.last_prompt
    assert "Startup Support" in FakeGeminiModel.last_prompt


def test_personalized_answer_uses_current_session_history(monkeypatch):
    service = ChatbotService()

    monkeypatch.setattr(service, "_get_authenticated_user_id", lambda token: "user-1")
    monkeypatch.setattr(
        service,
        "_fetch_profile",
        lambda user_id: {"occupation": "Student", "state": "Kerala"},
    )
    monkeypatch.setattr(
        service,
        "retrieve_sources",
        lambda query, limit=5, fetch_k=20, search_type="mmr": [
            {
                "type": "scheme",
                "scheme_id": "pmegp",
                "title": "PMEGP",
                "category": "Entrepreneurship",
                "state": "All India",
                "application_link": "https://www.kviconline.gov.in",
                "snippet": "Credit-linked subsidy programme.",
            }
        ],
    )
    monkeypatch.setattr(chatbot_module, "ChatGoogleGenerativeAI", FakeGeminiModel)

    service.answer_personalized_question(
        "token",
        "Am I eligible?",
        history=[
            {"role": "user", "content": "Tell me about PMEGP."},
            {"role": "assistant", "content": "PMEGP is a credit-linked subsidy programme."},
        ],
    )

    assert "User: Tell me about PMEGP." in FakeGeminiModel.last_prompt
    assert "Current User Question\nAm I eligible?" in FakeGeminiModel.last_prompt


def test_dynamic_query_routing_only_uses_web_for_recent_information():
    service = ChatbotService()

    assert service.should_use_web_search("What is the deadline for PMEGP?") is True
    assert service.should_use_web_search("Are applications open currently?") is True
    assert service.should_use_web_search("Tell me about PMEGP eligibility") is False


def test_web_search_failure_returns_unverified_fallback(monkeypatch):
    def raise_network_error(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(web_search_module.httpx, "get", raise_network_error)

    results = WebSearchService().search_official_sources("PMEGP deadline")

    assert results == [UNVERIFIED_WEB_RESULT]


def test_web_search_ignores_unofficial_results():
    html = """
    <a class="result__a" href="https://example.com/blog">Unofficial blog</a>
    <a class="result__snippet">Unofficial summary</a>
    <a class="result__a" href="https://scholarships.gov.in">Official portal</a>
    <a class="result__snippet">Official notification page</a>
    """

    results = WebSearchService()._parse_results(html, limit=3)

    assert len(results) == 1
    assert results[0]["verified"] is True
    assert results[0]["url"] == "https://scholarships.gov.in"


class FakeWebResponse:
    def __init__(
        self,
        text: str = "",
        content: bytes | None = None,
        url: str = "https://scholarships.gov.in",
        content_type: str = "text/html",
        status_code: int = 200,
    ) -> None:
        self.text = text
        self.content = content if content is not None else text.encode()
        self.url = url
        self.headers = {"content-type": content_type}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")
        return None


class FakeWebClient:
    def __init__(self, responses: dict[str, FakeWebResponse]) -> None:
        self.responses = responses

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str) -> FakeWebResponse:
        return self.responses[url]

    def head(self, url: str) -> FakeWebResponse:
        return self.responses[url]


def test_web_search_extracts_visible_text_from_official_html_page():
    html = """
    <html>
      <head><style>.hidden{display:none}</style><script>ignore()</script></head>
      <body>
        <header>Navigation junk</header>
        <main>
          <h1>Central Sector Scholarship Renewal</h1>
          <p>Renewal applications are open until 31 December 2026.</p>
        </main>
        <footer>Footer junk</footer>
      </body>
    </html>
    """
    client = FakeWebClient(
        {
            "https://scholarships.gov.in/renewal": FakeWebResponse(
                text=html,
                url="https://scholarships.gov.in/renewal",
            )
        }
    )

    text = WebSearchService()._fetch_official_text(client, "https://scholarships.gov.in/renewal")

    assert "Central Sector Scholarship Renewal" in text
    assert "31 December 2026" in text
    assert "Navigation junk" not in text
    assert "ignore()" not in text


def test_web_search_enriches_results_with_extracted_official_content(monkeypatch):
    service = WebSearchService()
    client = FakeWebClient(
        {
            "https://pmay-urban.gov.in/notification": FakeWebResponse(
                text="<main><p>Latest PMAY notification was published on 1 June 2026.</p></main>",
                url="https://pmay-urban.gov.in/notification",
            )
        }
    )
    results = [
        {
            "type": "web",
            "title": "PMAY notification",
            "url": "https://pmay-urban.gov.in/notification",
            "snippet": "Latest notification",
            "content": "",
            "verified": True,
        }
    ]

    monkeypatch.setattr(web_search_module.httpx, "Client", lambda **kwargs: client)
    enriched = service._enrich_results(results)

    assert enriched[0]["verified"] is True
    assert "Latest PMAY notification" in enriched[0]["content"]
    assert enriched[0]["official_page_state"] == "verified"


def test_web_search_prefers_final_reachable_url_after_redirect(monkeypatch):
    service = WebSearchService()
    client = FakeWebClient(
        {
            "https://old.nic.in/notice": FakeWebResponse(
                text="<main><p>Latest notification details are available.</p></main>",
                url="https://new.nic.in/notice",
            ),
            "https://new.nic.in/notice": FakeWebResponse(
                text="<main><p>Latest notification details are available.</p></main>",
                url="https://new.nic.in/notice",
            ),
        }
    )
    results = [
        {
            "type": "web",
            "title": "Official notification",
            "url": "https://old.nic.in/notice",
            "snippet": "",
            "content": "",
            "verified": True,
        }
    ]

    monkeypatch.setattr(web_search_module.httpx, "Client", lambda **kwargs: client)
    enriched = service._enrich_results(results)

    assert enriched[0]["url"] == "https://new.nic.in/notice"
    assert enriched[0]["verified"] is True


def test_web_search_ignores_unreachable_official_url(monkeypatch):
    service = WebSearchService()
    client = FakeWebClient(
        {
            "https://broken.gov.in": FakeWebResponse(
                text="Not found",
                url="https://broken.gov.in",
                status_code=404,
            )
        }
    )
    results = [
        {
            "type": "web",
            "title": "Broken official portal",
            "url": "https://broken.gov.in",
            "snippet": "",
            "content": "",
            "verified": True,
        }
    ]

    monkeypatch.setattr(web_search_module.httpx, "Client", lambda **kwargs: client)

    assert service._enrich_results(results) == []


def test_web_search_uses_minimal_override_when_stale_known_portal_fails(monkeypatch):
    service = WebSearchService()
    client = FakeWebClient(
        {
            "https://old.gov.in/nsp": FakeWebResponse(
                text="Gone",
                url="https://old.gov.in/nsp",
                status_code=404,
            ),
            "https://scholarships.gov.in": FakeWebResponse(
                text="<main><p>National Scholarship Portal renewal notification details are available.</p></main>",
                url="https://scholarships.gov.in",
            ),
        }
    )
    results = [
        {
            "type": "web",
            "title": "NSP old portal",
            "url": "https://old.gov.in/nsp",
            "snippet": "National Scholarship Portal",
            "content": "",
            "verified": True,
        }
    ]

    monkeypatch.setattr(web_search_module.httpx, "Client", lambda **kwargs: client)
    enriched = service._enrich_results(results)

    assert enriched[0]["url"] == "https://scholarships.gov.in"
    assert enriched[0]["verified"] is True


def test_web_search_marks_loading_page_as_placeholder(monkeypatch):
    service = WebSearchService()
    client = FakeWebClient(
        {
            "https://scholarships.gov.in": FakeWebResponse(
                text="<main><h1>New Experience Loading...</h1><p>Stay tuned. Portal is Now Live.</p></main>",
                url="https://scholarships.gov.in",
            )
        }
    )
    results = [
        {
            "type": "web",
            "title": "National Scholarship Portal",
            "url": "https://scholarships.gov.in",
            "snippet": "",
            "content": "",
            "verified": True,
        }
    ]

    monkeypatch.setattr(web_search_module.httpx, "Client", lambda **kwargs: client)
    enriched = service._enrich_results(results)

    assert enriched[0]["official_page_state"] == "placeholder"
    assert enriched[0]["verified"] is False


def test_web_search_marks_maintenance_page(monkeypatch):
    service = WebSearchService()
    client = FakeWebClient(
        {
            "https://example.gov.in": FakeWebResponse(
                text="<main><p>Portal under maintenance. Please try again later.</p></main>",
                url="https://example.gov.in",
            )
        }
    )
    results = [
        {
            "type": "web",
            "title": "Official portal",
            "url": "https://example.gov.in",
            "snippet": "",
            "content": "",
            "verified": True,
        }
    ]

    monkeypatch.setattr(web_search_module.httpx, "Client", lambda **kwargs: client)
    enriched = service._enrich_results(results)

    assert enriched[0]["official_page_state"] == "maintenance"
    assert enriched[0]["verified"] is False


def test_web_search_marks_migrated_portal_as_placeholder(monkeypatch):
    service = WebSearchService()
    client = FakeWebClient(
        {
            "https://example.gov.in/new": FakeWebResponse(
                text="<main><p>Migrated portal with enhanced experience launching soon.</p><p>Countdown begins.</p></main>",
                url="https://example.gov.in/new",
            )
        }
    )
    results = [
        {
            "type": "web",
            "title": "Migrated portal",
            "url": "https://example.gov.in/new",
            "snippet": "",
            "content": "",
            "verified": True,
        }
    ]

    monkeypatch.setattr(web_search_module.httpx, "Client", lambda **kwargs: client)
    enriched = service._enrich_results(results)

    assert enriched[0]["official_page_state"] == "placeholder"
    assert enriched[0]["verified"] is False


def test_web_search_keeps_normal_official_page_verified():
    text = (
        "Central Sector Scholarship renewal applications must be submitted through NSP. "
        "Eligibility, documents, guidelines, notification, and last date details are listed here. "
        "The last date is 31 December 2026."
    )

    assert WebSearchService()._classify_official_page_state(text) == "verified"


def test_web_search_decodes_duckduckgo_redirect_url():
    url = "/l/?uddg=https%3A%2F%2Fscholarships.gov.in%2Ffresh%2Frenewal"

    cleaned = WebSearchService()._clean_result_url(url)

    assert cleaned == "https://scholarships.gov.in/fresh/renewal"


def test_web_search_handles_pdf_text_when_extractor_available(monkeypatch):
    monkeypatch.setattr(WebSearchService, "_extract_pdf_text", lambda self, content: "PDF notification text")
    client = FakeWebClient(
        {
            "https://example.gov.in/notice.pdf": FakeWebResponse(
                content=b"%PDF sample",
                url="https://example.gov.in/notice.pdf",
                content_type="application/pdf",
            )
        }
    )

    text = WebSearchService()._fetch_official_text(client, "https://example.gov.in/notice.pdf")

    assert text == "PDF notification text"


def test_personalized_prompt_includes_extracted_web_content():
    prompt = ChatbotService()._build_personalized_prompt(
        question="Is PM Vishwakarma currently open?",
        profile_context="State: Kerala",
        history_context="No recent conversation in this session.",
        sources=[],
        web_results=[
            {
                "title": "PM Vishwakarma",
                "url": "https://pmvishwakarma.gov.in",
                "snippet": "Official portal",
                "content": "Applications are currently being accepted through the official portal.",
                "verified": True,
            }
        ],
    )

    assert "Extracted official content: Applications are currently being accepted" in prompt


def test_personalized_prompt_disallows_greetings_and_requires_direct_format():
    prompt = ChatbotService()._build_personalized_prompt(
        question="What is the renewal deadline for Central Sector Scholarship under NSP?",
        profile_context="State: Kerala",
        history_context="No recent conversation in this session.",
        sources=[],
        web_results=[],
    )

    assert "Do not use greetings" in prompt
    assert "plain text section labels only: Answer, Key Details, Eligibility, Next Steps, Official Source" in prompt
    assert "Do not wrap section labels in markdown markers" in prompt
    assert "generic assumptions" in prompt
    assert "explain why verification was not possible" in prompt
    assert "do not print raw URLs" in prompt


def test_response_sources_remove_internal_duplicates_and_low_relevance():
    service = ChatbotService()
    sources = [
        {
            "type": "web",
            "title": "Official source verification",
            "url": "",
            "verified": False,
            "snippet": "I could not verify this information from official sources.",
        },
        {
            "type": "scheme",
            "scheme_id": "central-sector",
            "title": "Central Sector Scheme of Scholarship for College and University Students",
            "category": "Scholarship",
            "state": "All India",
            "snippet": "Renewal is submitted through the National Scholarship Portal.",
        },
        {
            "type": "scheme",
            "scheme_id": "central-sector",
            "title": "Central Sector Scheme of Scholarship for College and University Students",
            "category": "Scholarship",
            "state": "All India",
            "snippet": "Duplicate source.",
        },
        {
            "type": "scheme",
            "scheme_id": "pm-scholarship",
            "title": "PM Scholarship Scheme",
            "category": "Scholarship",
            "state": "All India",
            "snippet": "Unrelated armed forces scholarship.",
        },
        {
            "type": "web",
            "title": "National Scholarship Portal",
            "url": "https://scholarships.gov.in",
            "verified": True,
            "content": "Central Sector Scholarship renewal application through NSP.",
        },
    ]

    filtered = service._filter_response_sources(
        "What is the renewal deadline for Central Sector Scholarship under NSP?",
        "Central Sector Scholarship Renewal. I could not verify this information from official sources.",
        sources,
    )

    assert len(filtered) <= 3
    assert all(source.get("title") != "Official source verification" for source in filtered)
    assert len([source for source in filtered if source.get("scheme_id") == "central-sector"]) == 1
    assert any(source.get("title") == "National Scholarship Portal" for source in filtered)


def test_follow_ups_are_contextual_for_renewal_questions():
    service = ChatbotService()

    follow_ups = service._generate_follow_ups(
        "What is the renewal deadline for Central Sector Scholarship under NSP?",
        "Central Sector Scholarship Renewal",
        [{"title": "National Scholarship Portal"}],
    )

    assert follow_ups == [
        "Renewal eligibility",
        "Required documents",
        "How to renew on NSP",
        "Latest NSP notifications",
    ]


def test_dynamic_unverified_response_limits_sources_to_relevant_scheme_and_portal(monkeypatch):
    service = ChatbotService()
    profile = {"state": "Kerala", "occupation": "Student"}
    retrieved_sources = [
        {
            "type": "scheme",
            "scheme_id": "central-sector",
            "title": "Central Sector Scheme of Scholarship for College and University Students",
            "category": "Scholarship",
            "state": "All India",
            "application_link": "https://scholarships.gov.in",
            "snippet": "Central Sector Scholarship renewal is handled on NSP.",
        },
        {
            "type": "scheme",
            "scheme_id": "pm-scholarship",
            "title": "PM Scholarship Scheme",
            "category": "Scholarship",
            "state": "All India",
            "application_link": "https://example.gov.in/pm-scholarship",
            "snippet": "Scholarship for a different applicant group.",
        },
        {
            "type": "scheme",
            "scheme_id": "egrantz",
            "title": "eGrantz Kerala",
            "category": "Scholarship",
            "state": "Kerala",
            "application_link": "https://example.gov.in/egrantz",
            "snippet": "State scholarship unrelated to Central Sector Scholarship.",
        },
    ]

    monkeypatch.setattr(service, "_get_authenticated_user_id", lambda token: "user-1")
    monkeypatch.setattr(service, "_fetch_profile", lambda user_id: profile)
    monkeypatch.setattr(service, "retrieve_sources", lambda *args, **kwargs: retrieved_sources)
    monkeypatch.setattr(
        chatbot_module.web_search_service,
        "search_official_sources",
        lambda *args, **kwargs: [
            {
                "type": "web",
                "title": "Official source verification",
                "url": "",
                "snippet": "I could not verify this information from official sources.",
                "content": "I could not verify this information from official sources.",
                "verified": False,
            }
        ],
    )

    response = service.answer_personalized_question(
        "token",
        "What is the renewal deadline for Central Sector Scholarship under NSP?",
        history=[],
    )

    assert response["answer"] == DYNAMIC_UNVERIFIED_RESPONSE
    assert "**Answer**" not in response["answer"]
    assert response["answer"].startswith("Answer\n• I could not verify the current information")
    assert len(response["sources"]) == 2
    assert response["sources"][0]["scheme_id"] == "central-sector"
    assert response["sources"][1]["title"] == "Official Portal"
    assert response["sources"][1]["url"] == "https://scholarships.gov.in"
    assert all(source.get("scheme_id") != "pm-scholarship" for source in response["sources"])
    assert all(source.get("scheme_id") != "egrantz" for source in response["sources"])


def test_dynamic_unverified_sources_never_exceed_two_cards():
    service = ChatbotService()
    sources = [
        {
            "type": "scheme",
            "scheme_id": "pmegp",
            "title": "PMEGP",
            "application_link": "https://www.kviconline.gov.in",
            "snippet": "Prime Minister Employment Generation Programme",
        },
        {
            "type": "scheme",
            "scheme_id": "other",
            "title": "Other entrepreneurship scheme",
            "application_link": "https://example.gov.in",
            "snippet": "Other scheme",
        },
    ]

    filtered = service._dynamic_unverified_sources("Last date for PMEGP", sources)

    assert len(filtered) <= 2
    assert filtered[0]["scheme_id"] == "pmegp"
    assert filtered[1]["title"] == "Official Portal"


def test_dynamic_placeholder_page_returns_explanatory_fallback_with_action(monkeypatch):
    service = ChatbotService()
    retrieved_sources = [
        {
            "type": "scheme",
            "scheme_id": "central-sector",
            "title": "Central Sector Scheme of Scholarship for College and University Students",
            "application_link": "https://scholarships.gov.in",
            "snippet": "Central Sector Scholarship renewal is handled on NSP.",
        },
        {
            "type": "scheme",
            "scheme_id": "unrelated",
            "title": "Unrelated Scholarship",
            "application_link": "https://example.gov.in/unrelated",
            "snippet": "Unrelated scholarship.",
        },
    ]

    monkeypatch.setattr(service, "_get_authenticated_user_id", lambda token: "user-1")
    monkeypatch.setattr(service, "_fetch_profile", lambda user_id: {"occupation": "Student"})
    monkeypatch.setattr(service, "retrieve_sources", lambda *args, **kwargs: retrieved_sources)
    monkeypatch.setattr(
        chatbot_module.web_search_service,
        "search_official_sources",
        lambda *args, **kwargs: [
            {
                "type": "web",
                "title": "National Scholarship Portal",
                "url": "https://scholarships.gov.in",
                "snippet": "New Experience Loading...",
                "content": "New Experience Loading... Stay tuned. Portal is Now Live.",
                "verified": False,
                "official_page_state": "placeholder",
            }
        ],
    )

    response = service.answer_personalized_question(
        "token",
        "What is the renewal deadline for Central Sector Scholarship under NSP?",
        history=[],
    )

    assert response["answer"] == DYNAMIC_PORTAL_PLACEHOLDER_RESPONSE
    assert "I could not verify this information" not in response["answer"]
    assert "transition or loading page" in response["answer"]
    assert response["sources"] == [
        {
            "type": "web",
            "title": "National Scholarship Portal",
            "url": "https://scholarships.gov.in",
            "snippet": "The official portal did not expose the requested information in extracted text.",
            "verified": False,
            "official_page_state": "placeholder",
        }
    ]
    assert response["action_links"] == [
        {
            "label": "Open Official Portal",
            "url": "https://scholarships.gov.in",
            "is_official": True,
        }
    ]


def test_action_links_are_deduped_by_url():
    service = ChatbotService()
    sources = [
        {
            "type": "scheme",
            "title": "Central Sector Scholarship",
            "application_link": "https://scholarships.gov.in",
        },
        {
            "type": "web",
            "title": "Official Portal",
            "url": "https://scholarships.gov.in",
            "verified": True,
        },
    ]

    links = service._generate_action_links("How do I renew on NSP?", sources)

    assert links == [
        {
            "label": "Renew on NSP",
            "url": "https://scholarships.gov.in",
            "is_official": True,
        }
    ]


def test_action_links_are_deduped_by_normalized_url():
    service = ChatbotService()
    sources = [
        {
            "type": "web",
            "title": "Portal",
            "url": "https://scholarships.gov.in/",
            "verified": True,
        },
        {
            "type": "scheme",
            "title": "Portal duplicate",
            "application_link": "https://scholarships.gov.in",
        },
    ]

    links = service._generate_action_links("latest notification", sources)

    assert len(links) == 1
    assert links[0]["url"] == "https://scholarships.gov.in/"


def test_relevance_gate_rejects_scholarships_for_health_query():
    service = ChatbotService()
    sources = [
        {
            "type": "scheme",
            "scheme_id": "pm-scholarship",
            "title": "PM Scholarship Scheme",
            "category": "Scholarship",
            "snippet": "Scholarship support for students with family income below a threshold.",
        },
        {
            "type": "scheme",
            "scheme_id": "egrantz",
            "title": "eGrantz Kerala",
            "category": "Scholarship",
            "snippet": "State scholarship for eligible students.",
        },
    ]

    filtered = service._filter_retrieved_sources_for_question(
        "Find health schemes for low income families.",
        sources,
        history=[],
    )

    assert filtered == []


def test_relevance_gate_keeps_recent_conversation_topic_for_follow_up():
    service = ChatbotService()
    sources = [
        {
            "type": "scheme",
            "scheme_id": "pmegp",
            "title": "PMEGP",
            "category": "Employment",
            "snippet": "Prime Minister Employment Generation Programme eligibility and subsidy details.",
        },
        {
            "type": "scheme",
            "scheme_id": "scholarship",
            "title": "Student Scholarship",
            "category": "Scholarship",
            "snippet": "Scholarship eligibility for students.",
        },
    ]

    filtered = service._filter_retrieved_sources_for_question(
        "Who is eligible?",
        sources,
        history=[{"role": "user", "content": "What is PMEGP?"}],
    )

    assert [source["scheme_id"] for source in filtered] == ["pmegp"]


def test_personalized_answer_returns_uncertainty_for_weak_retrieval(monkeypatch):
    service = ChatbotService()
    weak_sources = [
        {
            "type": "scheme",
            "scheme_id": "pm-scholarship",
            "title": "PM Scholarship Scheme",
            "category": "Scholarship",
            "application_link": "https://example.gov.in/scholarship",
            "snippet": "Scholarship support for students with family income below a threshold.",
        }
    ]

    monkeypatch.setattr(service, "_get_authenticated_user_id", lambda token: "user-1")
    monkeypatch.setattr(service, "_fetch_profile", lambda user_id: {})
    monkeypatch.setattr(service, "retrieve_sources", lambda *args, **kwargs: weak_sources)

    response = service.answer_personalized_question(
        "token",
        "Find health schemes for low income families.",
        history=[],
    )

    assert response["answer"] == INSUFFICIENT_RELEVANCE_RESPONSE
    assert response["sources"] == []
    assert response["action_links"] == []
    assert response["follow_ups"] == [
        "Eligibility",
        "State-specific schemes",
        "Required documents",
        "Application process",
    ]


def test_embedding_normalization_handles_supported_embedding_shapes():
    service = ChatbotService()

    assert service._normalize_embedding(None) == []
    assert service._normalize_embedding([]) == []
    assert service._normalize_embedding(np.array([])) == []
    assert service._normalize_embedding([1, 2, 3]) == [1.0, 2.0, 3.0]
    assert service._normalize_embedding(np.array([1, 2, 3])) == [1.0, 2.0, 3.0]


def test_cosine_similarity_handles_none_empty_lists_and_numpy_arrays():
    service = ChatbotService()

    assert service._cosine_similarity(None, [1, 0]) == 0.0
    assert service._cosine_similarity([], [1, 0]) == 0.0
    assert service._cosine_similarity(np.array([]), [1, 0]) == 0.0
    assert service._cosine_similarity([1, 0], np.array([1, 0])) == 1.0
    assert service._cosine_similarity(np.array([1, 0]), [0, 1]) == 0.0


def test_mmr_selection_handles_mixed_embedding_types_without_truthiness_errors():
    service = ChatbotService()
    sources = [
        {"title": "None embedding", "embedding": None},
        {"title": "Empty list", "embedding": []},
        {"title": "Empty numpy", "embedding": np.array([])},
        {"title": "Python list", "embedding": [1, 0]},
        {"title": "Numpy array", "embedding": np.array([0, 1])},
    ]

    selected = service._select_mmr_sources([1, 0], sources, limit=2)

    assert len(selected) == 2
    assert {source["title"] for source in selected} == {"Python list", "Numpy array"}
