"""Build the right adapter for a models.yaml entry."""
import os

from .adapters import AnthropicAdapter
from .adapters_gemini import GeminiAdapter
from .adapters_oai import OpenAIChatAdapter

OPENROUTER_URL = "https://openrouter.ai/api/v1"
OPENAI_URL = "https://api.openai.com/v1"


def make_adapter(model_key: str, cfg: dict):
    api_model = cfg.get("api_model", model_key)
    prov = cfg["provider"]
    if prov == "anthropic":
        return AnthropicAdapter(api_model, cfg)
    if prov == "openai":
        return OpenAIChatAdapter(api_model, cfg, OPENAI_URL, os.environ.get("OPENAI_API_KEY"))
    if prov == "openrouter":
        return OpenAIChatAdapter(api_model, cfg, OPENROUTER_URL, os.environ.get("OPENROUTER_API_KEY"), openrouter=True)
    if prov == "gemini":
        return GeminiAdapter(api_model, cfg, os.environ.get("GEMINI_API_KEY"))
    raise ValueError(f"unknown provider {prov}")
