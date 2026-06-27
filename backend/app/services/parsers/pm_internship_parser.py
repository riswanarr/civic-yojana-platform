from typing import Any

from app.services.parsers.base_parser import BaseParser


class PMInternshipParser(BaseParser):
    parser_name = "pm_internship"

    def fetch(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            self.mock_opportunity(
                source=source,
                title="PM Internship Opportunity Update",
                description="Mock internship opportunity update from the PM Internship portal.",
                category="Internship",
            )
        ]
