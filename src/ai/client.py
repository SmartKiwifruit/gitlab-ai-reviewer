import httpx


class AIClient:
    """Multi-provider AI API client."""

    PROVIDERS = {
        "claude": {
            "url": "https://api.anthropic.com/v1/messages",
            "headers": {"anthropic-version": "2023-06-01"},
        },
        "openai": {
            "url": "https://api.openai.com/v1/chat/completions",
            "headers": {},
        },
        "qwen": {
            "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            "headers": {},
        },
    }

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        base_url: str | None = None,
        httpx_client: httpx.Client | None = None,
    ):
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Supported: {list(self.PROVIDERS.keys())}")

        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = base_url
        self._http = httpx_client or httpx.Client(timeout=120.0)

    def review(self, system_prompt: str, user_prompt: str) -> str:
        """Send review request and return raw text response."""
        config = self.PROVIDERS[self.provider]

        if self.provider == "claude":
            return self._call_claude(config, system_prompt, user_prompt)
        elif self.provider == "openai":
            return self._call_openai(config, system_prompt, user_prompt)
        elif self.provider == "qwen":
            return self._call_qwen(config, system_prompt, user_prompt)

    def _call_claude(self, config, system_prompt, user_prompt):
        if self.base_url:
            url = self.base_url.rstrip("/") + "/v1/messages"
        else:
            url = config["url"]
        self._http.headers.update({
            "x-api-key": self.api_key,
            "content-type": "application/json",
            **config["headers"],
        })
        resp = self._http.post(url, json={
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        })
        resp.raise_for_status()
        data = resp.json()
        # Find the text block (may be preceded by thinking block)
        for block in data["content"]:
            if block.get("type") == "text":
                return block["text"]
        return data["content"][0].get("text", str(data["content"][0]))

    def _call_openai(self, config, system_prompt, user_prompt):
        self._http.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        })
        resp = self._http.post(config["url"], json={
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        })
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_qwen(self, config, system_prompt, user_prompt):
        self._http.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        })
        resp = self._http.post(config["url"], json={
            "model": self.model,
            "input": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            "parameters": {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            },
        })
        resp.raise_for_status()
        return resp.json()["output"]["text"]
