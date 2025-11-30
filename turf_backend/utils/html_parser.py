from bs4 import BeautifulSoup


class HTMLParser:
    @classmethod
    def find_all(cls, html: str, tag: str, **kwargs: dict[str, str]) -> list[str]:
        return BeautifulSoup(html, "html.parser").find_all(tag, **kwargs)
