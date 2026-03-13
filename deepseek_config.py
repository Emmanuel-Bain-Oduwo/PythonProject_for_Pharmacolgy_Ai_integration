import os
import logging
from typing import List, Dict, Optional

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

load_dotenv()

log = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


def get_api_key() -> str:
    """Get API key from Streamlit secrets or environment."""
    if "DEEPSEEK_API_KEY" in st.secrets:
        return st.secrets["DEEPSEEK_API_KEY"]

    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        return key

    return ""


def get_sync_client():
    key = get_api_key()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")

    return OpenAI(
        api_key=key,
        base_url=DEEPSEEK_BASE_URL
    )


def get_async_client():
    key = get_api_key()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")

    return AsyncOpenAI(
        api_key=key,
        base_url=DEEPSEEK_BASE_URL
    )


async def deepseek_chat(messages: List[Dict],
                        model: str = DEEPSEEK_MODEL,
                        max_tokens: int = 2000,
                        temperature: float = 0.3) -> str:
    try:
        client = get_async_client()

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


def deepseek_chat_sync(messages: List[Dict],
                       model: str = DEEPSEEK_MODEL,
                       max_tokens: int = 2000,
                       temperature: float = 0.3) -> str:
    try:
        client = get_sync_client()

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


def deepseek_stream_sync(messages: List[Dict],
                         model: str = DEEPSEEK_MODEL,
                         max_tokens: int = 2000):

    try:
        client = get_sync_client()

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


def build_pharmacist_messages(query: str,
                              role: str = "doctor",
                              patient_context: Optional[Dict] = None,
                              history: Optional[List[Dict]] = None) -> List[Dict]:

    system = f"""
You are a senior clinical pharmacist with 20+ years of experience.

User role: {role.title()}

Provide evidence-based clinical answers.

Include:
• Mechanism of action
• Clinical uses
• Standard dosing
• Major drug interactions
• Monitoring parameters

Use clear headers and bullet points.
⚠️ Include safety warnings when relevant.
Remind that responses do not replace clinical judgement.
"""

    if patient_context:
        system += f"\n\nPatient Context:\n{patient_context}"

    messages = [{"role": "system", "content": system}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": query})

    return messages
