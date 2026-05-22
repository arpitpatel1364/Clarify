"""
Clarify — AI Provider Router
Supports: Claude, OpenAI, Gemini, Groq, Ollama, OpenRouter
All providers support streaming via callbacks.
"""
from __future__ import annotations
import threading
from typing import Callable, Optional

from db.database import get_db, get_or_create_provider
from core.crypto import decrypt
from config.settings import settings


EXPLAIN_SYSTEM = """You are Clarify, an intelligent explainer assistant.
When given selected text, explain it clearly and concisely.
- Adapt your explanation style based on the content (technical, legal, medical, code, etc.)
- Use simple language unless the user asks for technical depth
- Keep explanations focused and useful
- Format with markdown where helpful (bold key terms, bullet points for lists)
- Be conversational, not robotic
"""

STYLE_PROMPTS = {
    "simple":    "Explain this in simple, everyday language anyone can understand:",
    "detailed":  "Give a thorough, detailed explanation of this:",
    "eli5":      "Explain this like I'm 5 years old:",
    "technical": "Give a precise technical explanation of this:",
    "summary":   "Summarize this briefly in 2-3 sentences:",
}


def _get_provider_key_and_model(provider: str) -> tuple[str, str, str]:
    db = get_db()
    cfg = get_or_create_provider(db, provider)
    key = decrypt(cfg.api_key or "")
    model = cfg.model or ""
    base_url = cfg.base_url or ""
    db.close()
    return key, model, base_url


def explain_text(
    text: str,
    on_token: Callable[[str], None],
    on_done: Callable[[str, int], None],
    on_error: Callable[[str], None],
    extra_messages: list | None = None,
):
    """Non-blocking: runs in a thread, calls callbacks."""
    provider = settings.ai.active_provider
    style = settings.ai.explain_style
    style_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["simple"])
    user_prompt = f"{style_prompt}\n\n{text}"

    thread = threading.Thread(
        target=_run_explanation,
        args=(provider, user_prompt, extra_messages or [], on_token, on_done, on_error),
        daemon=True,
    )
    thread.start()


def _run_explanation(provider, user_prompt, extra_messages, on_token, on_done, on_error):
    try:
        key, model, base_url = _get_provider_key_and_model(provider)
        if not key and provider not in ("ollama",):
            on_error(f"No API key set for {provider}. Please add it in Settings → AI Providers.")
            return

        if provider == "claude":
            _stream_claude(key, model, user_prompt, extra_messages, on_token, on_done)
        elif provider == "openai":
            _stream_openai(key, model, user_prompt, extra_messages, on_token, on_done, base_url)
        elif provider == "gemini":
            _stream_gemini(key, model, user_prompt, extra_messages, on_token, on_done)
        elif provider == "groq":
            _stream_openai(key, model, user_prompt, extra_messages, on_token, on_done,
                           base_url="https://api.groq.com/openai/v1")
        elif provider == "ollama":
            _stream_ollama(model, user_prompt, extra_messages, on_token, on_done, base_url)
        elif provider == "openrouter":
            _stream_openai(key, model, user_prompt, extra_messages, on_token, on_done,
                           base_url="https://openrouter.ai/api/v1")
        else:
            on_error(f"Unknown provider: {provider}")
    except Exception as e:
        on_error(str(e))


def _build_messages(user_prompt, extra_messages):
    msgs = []
    for m in extra_messages:
        msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": user_prompt})
    return msgs


# ── Claude ────────────────────────────────────────────────────────────────────
def _stream_claude(key, model, user_prompt, extra_messages, on_token, on_done):
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    full = ""
    tokens = 0
    messages = _build_messages(user_prompt, extra_messages)
    with client.messages.stream(
        model=model or "claude-sonnet-4-20250514",
        max_tokens=settings.ai.max_tokens,
        system=EXPLAIN_SYSTEM,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            full += text
            on_token(text)
        usage = stream.get_final_message().usage
        tokens = usage.input_tokens + usage.output_tokens
    on_done(full, tokens)


# ── OpenAI-compatible (OpenAI, Groq, OpenRouter) ─────────────────────────────
def _stream_openai(key, model, user_prompt, extra_messages, on_token, on_done, base_url=""):
    from openai import OpenAI
    kwargs = {"api_key": key}
    if base_url:
        kwargs["base_url"] = base_url
    client = OpenAI(**kwargs)
    messages = [{"role": "system", "content": EXPLAIN_SYSTEM}]
    messages += _build_messages(user_prompt, extra_messages)
    full = ""
    tokens = 0
    with client.chat.completions.create(
        model=model or "gpt-4o",
        messages=messages,
        max_tokens=settings.ai.max_tokens,
        temperature=settings.ai.temperature,
        stream=True,
        stream_options={"include_usage": True},
    ) as stream:
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                full += delta
                on_token(delta)
            if chunk.usage:
                tokens = chunk.usage.total_tokens
    on_done(full, tokens)


# ── Gemini ────────────────────────────────────────────────────────────────────
def _stream_gemini(key, model, user_prompt, extra_messages, on_token, on_done):
    import google.generativeai as genai
    genai.configure(api_key=key)
    gmodel = genai.GenerativeModel(
        model_name=model or "gemini-1.5-flash",
        system_instruction=EXPLAIN_SYSTEM,
    )
    prompt = user_prompt
    full = ""
    for chunk in gmodel.generate_content(prompt, stream=True):
        t = chunk.text or ""
        full += t
        if t:
            on_token(t)
    on_done(full, 0)


# ── Ollama ────────────────────────────────────────────────────────────────────
def _stream_ollama(model, user_prompt, extra_messages, on_token, on_done, base_url):
    import requests, json
    url = (base_url or "http://localhost:11434") + "/api/chat"
    messages = [{"role": "system", "content": EXPLAIN_SYSTEM}]
    messages += _build_messages(user_prompt, extra_messages)
    resp = requests.post(url, json={"model": model or "llama3.2:3b", "messages": messages, "stream": True}, stream=True)
    full = ""
    for line in resp.iter_lines():
        if line:
            data = json.loads(line)
            t = data.get("message", {}).get("content", "")
            full += t
            if t:
                on_token(t)
            if data.get("done"):
                break
    on_done(full, 0)
