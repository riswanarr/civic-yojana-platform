from app.services.parsers import AICTEParser, NCSParser, NSPParser


def test_nsp_parser_extracts_scholarship_links(monkeypatch):
    parser = NSPParser()
    html = """
    <html>
      <body>
        <a href="/student">Students can apply for NSP scholarship schemes</a>
      </body>
    </html>
    """
    monkeypatch.setattr(parser, "fetch_url", lambda url: html)

    items = parser.fetch({"url": "https://scholarships.gov.in/"})

    assert items[0]["title"] == "Students can apply for NSP scholarship schemes"
    assert items[0]["category"] == "Scholarship"
    assert items[0]["application_link"] == "https://scholarships.gov.in/student"


def test_ncs_parser_extracts_job_links(monkeypatch):
    parser = NCSParser()
    html = """
    <html>
      <body>
        <a href="/job-fair">Mega Job Fair for graduate candidates</a>
      </body>
    </html>
    """
    monkeypatch.setattr(parser, "fetch_url", lambda url: html)

    items = parser.fetch({"url": "https://www.ncs.gov.in/"})

    assert items[0]["title"] == "Mega Job Fair for graduate candidates"
    assert items[0]["category"] == "Government Job"
    assert items[0]["application_link"] == "https://www.ncs.gov.in/job-fair"


def test_aicte_parser_extracts_student_opportunity_links(monkeypatch):
    parser = AICTEParser()
    html = """
    <html>
      <body>
        <a href="/schemes/students">AICTE scholarship announcement for technical students</a>
      </body>
    </html>
    """
    monkeypatch.setattr(parser, "fetch_url", lambda url: html)

    items = parser.fetch({"url": "https://www.aicte.gov.in/"})

    assert items[0]["title"] == "AICTE scholarship announcement for technical students"
    assert items[0]["category"] == "Scholarship"
    assert items[0]["application_link"] == "https://www.aicte.gov.in/schemes/students"
