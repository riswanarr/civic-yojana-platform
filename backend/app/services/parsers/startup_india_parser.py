from typing import Any

from app.services.parsers.base_parser import BaseParser


class StartupIndiaParser(BaseParser):
    parser_name = "startup_india"

    def fetch(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            self.mock_opportunity(
                source=source,
                title="Startup India Opportunity Update",
                description="Mock startup support and innovation opportunity update.",
                category="Startup / Job Creation",
            )
        ]
