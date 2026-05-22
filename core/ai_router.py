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
    with get_db() as db:
        cfg = get_or_create_provider(db, provider)
        key = decrypt(cfg.api_key or "")
        model = cfg.model or ""
        base_url = cfg.base_url or ""
    return key, model, base_url


def explain_text(
    text: str,
    on_token: Callable[[str], None],
    on_done: Callable[[str, int], None],
    on_error: Callable[[str], None],
    extra_messages: list | None = None,
    original_text: str = "",
    mode: str = "explain",
):
    """Non-blocking: runs in a thread, calls callbacks."""
    provider = settings.ai.active_provider
    
    text_for_detection = original_text if original_text else text
    content_type = detect_content_type(text_for_detection)
    system_prompt = build_system_prompt(content_type)
    
    if mode == "explain":
        style = settings.ai.explain_style
        user_prompt = build_explain_prompt(text, style)
        messages_to_send = extra_messages or []
    elif mode == "chat":
        user_prompt = text
        messages_to_send = extra_messages or []
    else:
        on_error(f"Unknown explain_text mode: {mode}")
        return

    thread = threading.Thread(
        target=_run_explanation,
        args=(provider, user_prompt, messages_to_send, on_token, on_done, on_error, system_prompt, mode),
        daemon=True,
    )
    thread.start()


def _run_explanation(provider, user_prompt, extra_messages, on_token, on_done, on_error, system_prompt, mode="explain"):
    try:
        key, model, base_url = _get_provider_key_and_model(provider)
        if not key and provider not in ("ollama",):
            on_error(f"No API key set for {provider}. Please add it in Settings → AI Providers.")
            return

        if mode == "chat":
            pass

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
            _stream_ollama(model, user_prompt, extra_messages, on_token, on_done, on_error, system_prompt, base_url)
        elif provider == "openrouter":
            _stream_openai(key, model, user_prompt, extra_messages, on_token, on_done, system_prompt,
                           base_url="https://openrouter.ai/api/v1")
        else:
            on_error(f"Unknown provider: {provider}")
    except Exception as e:
        on_error(f"Unexpected error in {provider}: {str(e)}")


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
    
    contents = []
    for m in (extra_messages or []):
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [m["content"]]})
    
    contents.append({"role": "user", "parts": [user_prompt]})
    
    full = ""
    for chunk in gmodel.generate_content(contents, stream=True):
        t = chunk.text or ""
        full += t
        if t:
            on_token(t)
    on_done(full, 0)


# ── Ollama ────────────────────────────────────────────────────────────────────
def _stream_ollama(model, user_prompt, extra_messages, on_token, on_done, on_error, system_prompt, base_url=""):
    import requests
    import json

    # Fix trailing slash in base_url
    base = (base_url or "http://localhost:11434").rstrip("/")
    url = base + "/api/chat"

    # Step 1: Check Ollama is running
    try:
        ping = requests.get(base + "/api/tags", timeout=3)
        ping.raise_for_status()
    except requests.exceptions.ConnectionError:
        on_error(
            "Ollama is not running.\n"
            "Start it with: ollama serve\n"
            "Then try again."
        )
        return
    except requests.exceptions.Timeout:
        on_error("Ollama connection timed out. Is it running on " + base + "?")
        return
    except Exception as e:
        on_error(f"Cannot reach Ollama at {base}: {e}")
        return

    # Step 2: Validate model exists
    model_name = model.strip() if model and model.strip() else "llama3"
    try:
        tags_data = ping.json()
        installed_models = [m["name"] for m in tags_data.get("models", [])]
        # Check exact match or prefix match (e.g. "llama3" matches "llama3:latest")
        model_found = any(
            m == model_name or m.startswith(model_name + ":") or model_name.startswith(m.split(":")[0])
            for m in installed_models
        )
        if not model_found and installed_models:
            # Use first available model and warn
            model_name = installed_models[0]
            on_token(f"[Model '{model}' not found. Using '{model_name}' instead]\n\n")
        elif not model_found and not installed_models:
            on_error(
                f"No models installed in Ollama.\n"
                f"Run: ollama pull llama3\n"
                f"Then try again."
            )
            return
    except Exception:
        pass  # If tags parsing fails, proceed anyway with model as-is

    # Step 3: Build messages
    messages = [{"role": "system", "content": system_prompt}]
    messages += _build_messages(user_prompt, extra_messages)

    # Step 4: Stream with proper timeout and error handling
    full = ""
    try:
        resp = requests.post(
            url,
            json={
                "model": model_name,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": settings.ai.temperature,
                    "num_predict": settings.ai.max_tokens,
                }
            },
            stream=True,
            timeout=(5, 120),  # (connect timeout, read timeout)
        )
        resp.raise_for_status()

        for line in resp.iter_lines(chunk_size=None):
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Check for Ollama error response
            if "error" in data:
                on_error(f"Ollama error: {data['error']}")
                return

            token = data.get("message", {}).get("content", "")
            if token:
                full += token
                on_token(token)

            if data.get("done", False):
                break

        if not full:
            on_error(
                "Ollama returned an empty response.\n"
                f"Check that model '{model_name}' is working:\n"
                f"Run: ollama run {model_name}"
            )
            return

        on_done(full, 0)

    except requests.exceptions.Timeout:
        if full:
            # Partial response — still deliver it
            on_done(full, 0)
        else:
            on_error("Ollama request timed out. The model may be too slow or not responding.")
    except requests.exceptions.ConnectionError:
        on_error("Lost connection to Ollama mid-stream. Is it still running?")
    except Exception as e:
        if full:
            on_done(full, 0)
        else:
            on_error(f"Ollama streaming error: {str(e)}")
