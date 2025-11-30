from typing import Any

from bs4 import BeautifulSoup


class HTMLParser:
    @classmethod
    def find_all(cls, html: str, tag: str, **kwargs: Any) -> list[dict[str, Any]]:
        return BeautifulSoup(html, "html.parser").find_all(tag, **kwargs)
