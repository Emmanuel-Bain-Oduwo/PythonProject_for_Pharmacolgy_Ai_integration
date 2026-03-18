import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, cast

import streamlit as st
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

load_dotenv()

log = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
OPENAI_MODEL = "gpt-4o"
CREATOR_RESPONSE = (
    "I was created by Doctor Bain Oduwo, an AI healthcare engineer from Kenya currently based in India. "
    "He has strong skills in AI, machine learning, data science, and MLOps, with deep focus on healthcare applications, "
    "especially pharmacology and medicinal chemistry. I am still under development, and Bain continues improving me "
    "to become one of the best medical-context AI assistants in the world."
)


def _secrets_paths() -> List[Path]:
    return [
        Path.home() / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / "secrets.toml",
    ]


def _safe_secrets() -> Dict:
    if not any(path.exists() for path in _secrets_paths()):
        return {}
    try:
        return dict(st.secrets)
    except Exception:
        return {}


def normalize_provider(provider: Optional[str]) -> str:
    value = (provider or "auto").strip().lower()
    if value in {"consensus", "dual", "both", "openai+deepseek"}:
        return "consensus"
    if value in {"deepseek", "deep seek", "ds"}:
        return "deepseek"
    if value in {"openai", "open ai", "gpt", "chatgpt"}:
        return "openai"
    return "auto"


def get_api_key(provider: str = "deepseek") -> str:
    """Get a provider API key from Streamlit secrets or environment."""
    provider = normalize_provider(provider)
    key_name = "OPENAI_API_KEY" if provider == "openai" else "DEEPSEEK_API_KEY"

    env_key = os.getenv(key_name, "").strip()
    if env_key:
        return env_key

    secrets = _safe_secrets()
    if key_name in secrets and secrets[key_name]:
        return str(secrets[key_name]).strip()

    return ""


def provider_available(provider: str) -> bool:
    return bool(get_api_key(provider))


def available_providers() -> List[str]:
    providers = []
    if provider_available("openai"):
        providers.append("openai")
    if provider_available("deepseek"):
        providers.append("deepseek")
    return providers


def _resolve_provider(provider: str = "auto") -> str:
    provider = normalize_provider(provider)
    if provider == "consensus":
        provider = "auto"
    if provider == "auto":
        if provider_available("openai"):
            return "openai"
        if provider_available("deepseek"):
            return "deepseek"
        return "openai"

    if provider_available(provider):
        return provider

    fallback = "deepseek" if provider == "openai" else "openai"
    if provider_available(fallback):
        return fallback

    return provider


def resolve_provider(provider: str = "auto") -> str:
    """Public helper for UI code to show the provider that will be used."""
    return _resolve_provider(provider)


def _provider_defaults(provider: str) -> tuple[str, Optional[str]]:
    provider = _resolve_provider(provider)
    if provider == "openai":
        return OPENAI_MODEL, None
    return DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


def get_sync_client(provider: str = "deepseek"):
    provider = _resolve_provider(provider)
    key = get_api_key(provider)
    if not key:
        raise RuntimeError(f"{provider.upper()}_API_KEY not configured")

    _, base_url = _provider_defaults(provider)
    if base_url:
        return OpenAI(api_key=key, base_url=base_url)
    return OpenAI(api_key=key)


def get_async_client(provider: str = "deepseek"):
    provider = _resolve_provider(provider)
    key = get_api_key(provider)
    if not key:
        raise RuntimeError(f"{provider.upper()}_API_KEY not configured")

    _, base_url = _provider_defaults(provider)
    if base_url:
        return AsyncOpenAI(api_key=key, base_url=base_url)
    return AsyncOpenAI(api_key=key)


async def deepseek_chat(messages: List[ChatCompletionMessageParam],
                        model: str = DEEPSEEK_MODEL,
                        max_tokens: int = 2000,
                        temperature: float = 0.3) -> str:
    try:
        client = get_async_client("deepseek")

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content

    except Exception as e:
        log.error("DeepSeek async error: %s", e)
        return f"⚠️ AI Error: {str(e)}"


def deepseek_chat_sync(messages: List[ChatCompletionMessageParam],
                       model: str = DEEPSEEK_MODEL,
                       max_tokens: int = 2000,
                       temperature: float = 0.3) -> str:
    try:
        client = get_sync_client("deepseek")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content

    except Exception as e:
        log.error("DeepSeek sync error: %s", e)
        return f"⚠️ AI Error: {str(e)}"


def deepseek_stream_sync(messages: List[ChatCompletionMessageParam],
                         model: str = DEEPSEEK_MODEL,
                         max_tokens: int = 2000):

    try:
        client = get_sync_client("deepseek")

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    except Exception as e:
        yield f"⚠️ AI Error: {str(e)}"


def chat_sync(messages: List[ChatCompletionMessageParam],
              provider: str = "auto",
              model: Optional[str] = None,
              max_tokens: int = 2000,
              temperature: float = 0.3) -> str:
    try:
        resolved = _resolve_provider(provider)
        client = get_sync_client(resolved)
        resolved_model, _ = _provider_defaults(resolved)

        response = client.chat.completions.create(
            model=model or resolved_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content
    except Exception as e:
        log.error("AI chat error (%s): %s", provider, e)
        return f"⚠️ AI Error: {str(e)}"


def stream_sync(messages: List[ChatCompletionMessageParam],
                provider: str = "auto",
                model: Optional[str] = None,
                max_tokens: int = 2000,
                temperature: float = 0.3):
    try:
        resolved = _resolve_provider(provider)
        client = get_sync_client(resolved)
        resolved_model, _ = _provider_defaults(resolved)

        stream = client.chat.completions.create(
            model=model or resolved_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        log.error("AI stream error (%s): %s", provider, e)
        yield f"⚠️ AI Error: {str(e)}"


def consensus_chat_sync(messages: List[ChatCompletionMessageParam],
                        max_tokens: int = 1800,
                        temperature: float = 0.2) -> str:
    """Combine OpenAI and DeepSeek drafts, then synthesize a final answer."""
    if not (provider_available("openai") and provider_available("deepseek")):
        return chat_sync(messages, provider="auto", max_tokens=max_tokens, temperature=temperature)

    openai_answer = chat_sync(messages, provider="openai", max_tokens=max_tokens, temperature=temperature)
    deepseek_answer = chat_sync(messages, provider="deepseek", max_tokens=max_tokens, temperature=temperature)

    if openai_answer.startswith("⚠️ AI Error") and not deepseek_answer.startswith("⚠️ AI Error"):
        return deepseek_answer
    if deepseek_answer.startswith("⚠️ AI Error") and not openai_answer.startswith("⚠️ AI Error"):
        return openai_answer

    synthesis_messages: List[ChatCompletionMessageParam] = [
        cast(
            ChatCompletionSystemMessageParam,
            cast(
                object,
                {
                    "role": "system",
                    "content": (
                        "You are a senior medical reviewer. Merge two model drafts into one best-practice answer. "
                        "Prioritize safety, contraindications, interaction risks, monitoring, and practical clarity. "
                        "If drafts conflict, choose the safer recommendation and mention uncertainty briefly."
                    ),
                },
            ),
        ),
        cast(
            ChatCompletionUserMessageParam,
            cast(
                object,
                {
                    "role": "user",
                    "content": (
                        "Draft A (OpenAI):\n"
                        f"{openai_answer}\n\n"
                        "Draft B (DeepSeek):\n"
                        f"{deepseek_answer}\n\n"
                        "Create one final, concise, professional medical answer."
                    ),
                },
            ),
        ),
    ]

    return chat_sync(synthesis_messages, provider="openai", max_tokens=max_tokens, temperature=0.1)


def build_pharmacist_messages(query: str,
                              role: str = "doctor",
                              patient_context: Optional[Dict] = None,
                              history: Optional[List[ChatCompletionMessageParam]] = None) -> List[ChatCompletionMessageParam]:

    system = f"""
You are a senior medical AI assistant specialising in pharmacology, medication safety, and clinical counselling.

User role: {role.title()}

Style requirements:
- Be professional, accurate, and easy to follow.
- Prefer concise clinical language for clinicians and plain language for patients.
- Use bullet points and clear headings when helpful.
- Call out red-flag safety issues, interactions, monitoring, contraindications, and escalation criteria.
- Do not invent details. If uncertain, say so and recommend checking an authoritative source.

Identity rule:
- If the user asks who created you or who made you, reply exactly: "{CREATOR_RESPONSE}"

Clinical focus:
- Mechanism of action
- Clinical uses
- Standard dosing
- Major drug interactions
- Monitoring parameters
- Relevant warnings
"""

    if patient_context:
        system += f"\n\nPatient Context:\n{patient_context}"

    messages: List[ChatCompletionMessageParam] = [
        cast(ChatCompletionSystemMessageParam, cast(object, {"role": "system", "content": system}))
    ]

    if history:
        messages.extend(history)

    messages.append(cast(ChatCompletionUserMessageParam, cast(object, {"role": "user", "content": query})))

    return messages
