from __future__ import annotations

from .http import HttpError, get_json


class NewsClient:
    def __init__(
        self,
        cryptopanic_api_key: str | None = None,
        newsapi_key: str | None = None,
        timeout: float = 12.0,
    ) -> None:
        self.cryptopanic_api_key = cryptopanic_api_key
        self.newsapi_key = newsapi_key
        self.timeout = timeout

    def catalyst_for(self, base_asset: str) -> str | None:
        if self.cryptopanic_api_key:
            catalyst = self._cryptopanic(base_asset)
            if catalyst:
                return catalyst
        if self.newsapi_key:
            return self._newsapi(base_asset)
        return None

    def _cryptopanic(self, base_asset: str) -> str | None:
        try:
            payload = get_json(
                "https://cryptopanic.com/api/v1/posts/",
                {
                    "auth_token": self.cryptopanic_api_key,
                    "currencies": base_asset,
                    "kind": "news",
                    "filter": "hot",
                    "public": "true",
                },
                timeout=self.timeout,
            )
        except HttpError:
            return None
        results = payload.get("results", [])
        if not results:
            return None
        item = results[0]
        title = item.get("title")
        domain = item.get("domain")
        return f"{title} ({domain})" if title and domain else title

    def _newsapi(self, base_asset: str) -> str | None:
        try:
            payload = get_json(
                "https://newsapi.org/v2/everything",
                {
                    "apiKey": self.newsapi_key,
                    "q": f"{base_asset} crypto",
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 1,
                },
                timeout=self.timeout,
            )
        except HttpError:
            return None
        articles = payload.get("articles", [])
        if not articles:
            return None
        article = articles[0]
        source = article.get("source", {}).get("name")
        title = article.get("title")
        return f"{title} ({source})" if title and source else title
