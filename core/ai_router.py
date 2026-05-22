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


STYLE_PROMPTS = {
    "simple":    "Explain the following in simple, everyday language anyone can understand.",
    "detailed":  "Give a thorough, detailed explanation of the following.",
    "eli5":      "Explain the following like I am 5 years old. Use an analogy if helpful.",
    "technical": "Give a precise technical explanation of the following. Assume expert audience.",
    "summary":   "Summarize the following in 2-3 sentences. Be extremely concise.",
}

def detect_content_type(text: str) -> str:
    text_lower = text.lower().strip()
    code_signals = [
        "def ", "function ", "class ", "import ", "const ", "let ", "var ",
        "=>", "->", "::", "{}","();", "return ", "if (", "for (", "#include",
        "SELECT ", "FROM ", "WHERE ", "public static",
    ]
    if any(sig in text for sig in code_signals):
        return "code"
    legal_signals = [
        "whereas", "hereinafter", "pursuant to", "notwithstanding",
        "indemnify", "liability", "arbitration", "jurisdiction",
        "plaintiff", "defendant", "aforementioned", "shall not",
    ]
    if any(sig in text_lower for sig in legal_signals):
        return "legal"
    medical_signals = [
        "diagnosis", "symptoms", "treatment", "dosage", "mg", "ml",
        "syndrome", "prognosis", "contraindicated", "pathology",
        "administered", "prescription", "adverse", "clinical",
    ]
    if any(sig in text_lower for sig in medical_signals):
        return "medical"
    science_signals = [
        "hypothesis", "methodology", "correlation", "coefficient",
        "et al", "doi:", "p-value", "statistical", "theorem",
        "equation", "formula", "wavelength", "frequency",
    ]
    if any(sig in text_lower for sig in science_signals):
        return "scientific"
    return "general"

CONTENT_TYPE_HINTS = {
    "code":       "The selected text is CODE. Explain what it does, its inputs/outputs, and any notable patterns or issues.",
    "legal":      "The selected text is LEGAL language. Translate to plain English. Highlight key obligations, rights, and risks.",
    "medical":    "The selected text is MEDICAL content. Explain in simple terms. Note if professional consultation is needed.",
    "scientific": "The selected text is SCIENTIFIC/ACADEMIC. Explain the core concept clearly, then add depth.",
    "general":    "",
}

def build_system_prompt(content_type: str) -> str:
    base = """You are TextLens, an intelligent explainer assistant embedded in the user's desktop.
Explain selected text clearly and concisely.
Use markdown: **bold** key terms, bullet points for lists, `code` for code.
Do not repeat the selected text. Do not start with "This text..."."""
    hint = CONTENT_TYPE_HINTS.get(content_type, "")
    if hint:
        return f"{base}\n\n{hint}"
    return base

def build_explain_prompt(selected_text: str, style: str) -> str:
    style_line = STYLE_PROMPTS.get(style, STYLE_PROMPTS["simple"])
    return (
        f"{style_line}\n\n"
        f'Selected text:\n"""\n{selected_text}\n"""'
    )


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
    original_text: str = "",
):
    """Non-blocking: runs in a thread, calls callbacks."""
    provider = settings.ai.active_provider
    style = settings.ai.explain_style
    
    text_for_detection = original_text if original_text else text
    content_type = detect_content_type(text_for_detection)
    system_prompt = build_system_prompt(content_type)
    
    if extra_messages:
        user_prompt = text
    else:
        user_prompt = build_explain_prompt(text, style)

    thread = threading.Thread(
        target=_run_explanation,
        args=(provider, user_prompt, extra_messages or [], on_token, on_done, on_error, system_prompt),
        daemon=True,
    )
    thread.start()


def _run_explanation(provider, user_prompt, extra_messages, on_token, on_done, on_error, system_prompt):
    try:
        key, model, base_url = _get_provider_key_and_model(provider)
        if not key and provider not in ("ollama",):
            on_error(f"No API key set for {provider}. Please add it in Settings → AI Providers.")
            return

        if provider == "claude":
            _stream_claude(key, model, user_prompt, extra_messages, on_token, on_done, system_prompt)
        elif provider == "openai":
            _stream_openai(key, model, user_prompt, extra_messages, on_token, on_done, system_prompt, base_url)
        elif provider == "gemini":
            _stream_gemini(key, model, user_prompt, extra_messages, on_token, on_done, system_prompt)
        elif provider == "groq":
            _stream_openai(key, model, user_prompt, extra_messages, on_token, on_done, system_prompt,
                           base_url="https://api.groq.com/openai/v1")
        elif provider == "ollama":
            _stream_ollama(model, user_prompt, extra_messages, on_token, on_done, system_prompt, base_url)
        elif provider == "openrouter":
            _stream_openai(key, model, user_prompt, extra_messages, on_token, on_done, system_prompt,
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
def _stream_claude(key, model, user_prompt, extra_messages, on_token, on_done, system_prompt):
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    full = ""
    tokens = 0
    messages = _build_messages(user_prompt, extra_messages)
    with client.messages.stream(
        model=model or "claude-sonnet-4-20250514",
        max_tokens=settings.ai.max_tokens,
        system=system_prompt,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            full += text
            on_token(text)
        usage = stream.get_final_message().usage
        tokens = usage.input_tokens + usage.output_tokens
    on_done(full, tokens)


# ── OpenAI-compatible (OpenAI, Groq, OpenRouter) ─────────────────────────────
def _stream_openai(key, model, user_prompt, extra_messages, on_token, on_done, system_prompt, base_url=""):
    from openai import OpenAI
    kwargs = {"api_key": key}
    if base_url:
        kwargs["base_url"] = base_url
    client = OpenAI(**kwargs)
    messages = [{"role": "system", "content": system_prompt}]
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
def _stream_gemini(key, model, user_prompt, extra_messages, on_token, on_done, system_prompt):
    import google.generativeai as genai
    genai.configure(api_key=key)
    gmodel = genai.GenerativeModel(
        model_name=model or "gemini-1.5-flash",
        system_instruction=system_prompt,
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
def _stream_ollama(model, user_prompt, extra_messages, on_token, on_done, system_prompt, base_url=""):
    import requests, json
    url = (base_url or "http://localhost:11434") + "/api/chat"
    messages = [{"role": "system", "content": system_prompt}]
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
