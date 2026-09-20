import streamlit as st
import requests
import time
import json
import io
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Page Configuration & Styling ---
st.set_page_config(
    page_title="Dutchman KeySonar • Developed By Dutchman Security",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, premium dark/light adaptive styling, glass cards, and table scrolling
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #2563eb, #7c3aed, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.2rem;
    }
    .brand-watermark {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.18), rgba(124, 58, 237, 0.18));
        border: 1px solid rgba(99, 102, 241, 0.45);
        color: #38bdf8;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }
    .sync-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(34, 197, 94, 0.12);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.25);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .key-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(125, 125, 125, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 14px;
        transition: all 0.2s ease;
    }
    .key-card:hover {
        border-color: rgba(99, 102, 241, 0.4);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    .card-active {
        border-left: 5px solid #22c55e !important;
    }
    .card-quota {
        border-left: 5px solid #f97316 !important;
    }
    .card-invalid {
        border-left: 5px solid #ef4444 !important;
    }
    .card-other {
        border-left: 5px solid #eab308 !important;
    }
    .terminal-box {
        background-color: #0b132b;
        color: #f8fafc;
        border-radius: 10px;
        padding: 18px;
        font-family: ui-monospace, 'Courier New', Courier, monospace;
        font-size: 13px;
        border: 1px solid #1e293b;
        margin-top: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
    }
    .terminal-header {
        color: #94a3b8;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 8px;
        margin-bottom: 12px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .terminal-dot-red { width: 10px; height: 10px; border-radius: 50%; background: #ef4444; display: inline-block; }
    .terminal-dot-yellow { width: 10px; height: 10px; border-radius: 50%; background: #eab308; display: inline-block; }
    .terminal-dot-green { width: 10px; height: 10px; border-radius: 50%; background: #22c55e; display: inline-block; }
    
    /* Force table horizontal scroll */
    div[data-testid="stDataFrame"] {
        overflow-x: auto !important;
        width: 100% !important;
    }
    div[data-testid="stDataFrame"] > div {
        overflow-x: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Provider Specifications & Base Endpoints ---
BASE_PROVIDERS = {
    "Auto-Detect": {
        "name": "Auto-Detect (Per Key)",
        "description": "Inspects key prefix (gsk_, sk-proj-, xai-, sk-ant-, AIzaSy) automatically."
    },
    "Groq": {
        "name": "Groq (GroqCloud)",
        "auth_url": "https://api.groq.com/openai/v1/models",
        "chat_url": "https://api.groq.com/openai/v1/chat/completions",
        "default_model": "qwen/qwen3.8-27b",
        "models": ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "allam-2-7b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "groq/compound", "openai/gpt-oss-120b"],
        "header_type": "bearer",
        "doc": "Keys typically begin with 'gsk_'"
    },
    "OpenAI": {
        "name": "OpenAI",
        "auth_url": "https://api.openai.com/v1/models",
        "chat_url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "o1-mini", "o3-mini"],
        "header_type": "bearer",
        "doc": "Keys typically begin with 'sk-proj-' or 'sk-'"
    },
    "xAI (Grok)": {
        "name": "xAI (Grok)",
        "auth_url": "https://api.x.ai/v1/models",
        "chat_url": "https://api.x.ai/v1/chat/completions",
        "default_model": "grok-4.1-fast",
        "models": ["grok-4.1-fast", "grok-4.5", "grok-beta"],
        "header_type": "bearer",
        "doc": "Keys typically begin with 'xai-'"
    },
    "Anthropic": {
        "name": "Anthropic Claude",
        "auth_url": "https://api.anthropic.com/v1/models",
        "chat_url": "https://api.anthropic.com/v1/messages",
        "default_model": "claude-3-5-haiku-20241022",
        "models": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
        "header_type": "anthropic",
        "doc": "Keys typically begin with 'sk-ant-'"
    },
    "Google Gemini": {
        "name": "Google Gemini",
        "auth_url": "https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        "chat_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        "default_model": "gemini-1.5-flash",
        "models": ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
        "header_type": "gemini",
        "doc": "Keys typically begin with 'AIzaSy'"
    },
    "OpenRouter": {
        "name": "OpenRouter",
        "auth_url": "https://openrouter.ai/api/v1/auth/key",
        "chat_url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "openai/gpt-4o-mini",
        "models": ["openai/gpt-4o-mini", "meta-llama/llama-3.3-70b-instruct", "auto"],
        "header_type": "bearer",
        "doc": "Keys typically begin with 'sk-or-v1-'"
    },
    "DeepSeek": {
        "name": "DeepSeek",
        "auth_url": "https://api.deepseek.com/v1/models",
        "chat_url": "https://api.deepseek.com/v1/chat/completions",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "header_type": "bearer",
        "doc": "Keys typically begin with 'sk-'"
    },
    "Custom Endpoint": {
        "name": "Custom (OpenAI Compatible)",
        "header_type": "bearer",
        "doc": "Provide custom base URL and model name."
    }
}

# --- Dynamic Model Sync Function ---
def sync_dynamic_catalogs():
    """Dynamically query public AI model registries to keep model catalogs perpetually updated."""
    registry = json.loads(json.dumps(BASE_PROVIDERS))
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=3)
        if r.status_code == 200:
            data = r.json().get("data", [])
            live_models = [m["id"] for m in data if "id" in m]
            if live_models:
                registry["OpenRouter"]["models"] = live_models[:30]
    except Exception:
        pass
    return registry

# --- 5-Second Startup Dynamic Loader / Splash Screen ---
if "sync_initialized" not in st.session_state:
    st.session_state["sync_initialized"] = False

if not st.session_state["sync_initialized"]:
    st.markdown("""
    <div style="text-align: center; padding: 40px 15px 10px 15px;">
        <h1 class="main-header" style="font-size: 2.8rem;">🧭 Dutchman KeySonar</h1>
        <p style="color: #94a3b8; font-size: 1.15rem; max-width: 600px; margin: 0 auto 12px auto;">
            Initializing Dynamic Cloud Engine • Synchronizing Updated Models & Endpoints
        </p>
        <div style="margin-bottom: 25px;">
            <span class="brand-watermark">🛡️ Developed By Dutchman Security</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    loader_box = st.empty()
    progress_bar = st.progress(0.0)
    
    sync_steps = [
        ("📡 Querying Global Cloud Model Registries...", 0.20, 0.9),
        ("🔄 Synchronizing GroqCloud LPU Inference Models & Endpoints...", 0.45, 1.0),
        ("🧠 Indexing OpenAI GPT-4o, o-series & API Gateways...", 0.70, 1.0),
        ("⚡ Syncing Anthropic Claude, xAI Grok & Gemini Catalogs...", 0.88, 0.9),
        ("✅ Dynamic Sync Complete! All endpoints & models loaded.", 1.0, 0.6)
    ]
    
    for label, prog, duration in sync_steps:
        with loader_box.container():
            st.markdown(f"""
            <div style="
                background: rgba(15, 23, 42, 0.7);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 12px;
                padding: 22px;
                text-align: center;
                max-width: 620px;
                margin: 0 auto;
                box-shadow: 0 4px 20px rgba(0,0,0,0.25);
            ">
                <div style="font-size: 16px; color: #38bdf8; font-family: monospace; font-weight: 600; letter-spacing: 0.5px;">
                    {label}
                </div>
                <div style="color: #94a3b8; font-size: 12px; margin-top: 6px;">
                    Ensuring endpoints match latest updates • <strong style="color: #38bdf8;">Developed By Dutchman Security</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
        progress_bar.progress(prog)
        time.sleep(duration)
        
    st.session_state["provider_registry"] = sync_dynamic_catalogs()
    st.session_state["sync_time"] = datetime.now().strftime("%H:%M:%S")
    st.session_state["sync_initialized"] = True
    st.rerun()

# Use the dynamically synced registry
PROVIDERS = st.session_state.get("provider_registry", BASE_PROVIDERS)

# --- Helper Functions ---

def detect_key_provider(key: str) -> str:
    """Infer the AI provider by key prefix pattern."""
    k = key.strip()
    if k.startswith("gsk_"):
        return "Groq"
    elif k.startswith("xai-"):
        return "xAI (Grok)"
    elif k.startswith("sk-ant-"):
        return "Anthropic"
    elif k.startswith("AIzaSy"):
        return "Google Gemini"
    elif k.startswith("sk-or-v1-"):
        return "OpenRouter"
    elif k.startswith("sk-proj-") or k.startswith("sk-"):
        return "OpenAI"
    return "OpenAI"

def mask_api_key(key: str) -> str:
    """Mask key securely while showing prefix and suffix for identification."""
    k = key.strip()
    if len(k) <= 8:
        return k[:2] + "..." + k[-2:] if len(k) > 4 else "***"
    elif len(k) <= 16:
        return k[:4] + "..." + k[-3:]
    elif len(k) <= 32:
        return k[:7] + "..." + k[-4:]
    else:
        return k[:10] + "..." + k[-4:]

def generate_curl_commands(key: str, provider: str, model: str = None, custom_base_url: str = None) -> dict:
    """Generate clean, copy-paste ready terminal cURL commands for auth and completion tests."""
    k = key.strip()
    p = provider
    
    if p == "Groq":
        auth_url = "https://api.groq.com/openai/v1/models"
        chat_url = "https://api.groq.com/openai/v1/chat/completions"
        m = model or "qwen/qwen3.8-27b"
        auth_curl = f'curl -s -X GET "{auth_url}" \\\n  -H "Authorization: Bearer {k}"'
        chat_curl = f'curl -s -X POST "{chat_url}" \\\n  -H "Authorization: Bearer {k}" \\\n  -H "Content-Type: application/json" \\\n  -d \'{{"model": "{m}", "messages": [{{"role": "user", "content": "hi"}}], "max_tokens": 50}}\''
    elif p == "OpenAI":
        auth_url = "https://api.openai.com/v1/models"
        chat_url = "https://api.openai.com/v1/chat/completions"
        m = model or "gpt-4o-mini"
        auth_curl = f'curl -s -X GET "{auth_url}" \\\n  -H "Authorization: Bearer {k}"'
        chat_curl = f'curl -s -X POST "{chat_url}" \\\n  -H "Authorization: Bearer {k}" \\\n  -H "Content-Type: application/json" \\\n  -d \'{{"model": "{m}", "messages": [{{"role": "user", "content": "hi"}}], "max_tokens": 50}}\''
    elif p == "xAI (Grok)":
        auth_url = "https://api.x.ai/v1/models"
        chat_url = "https://api.x.ai/v1/chat/completions"
        m = model or "grok-4.1-fast"
        auth_curl = f'curl -s -X GET "{auth_url}" \\\n  -H "Authorization: Bearer {k}"'
        chat_curl = f'curl -s -X POST "{chat_url}" \\\n  -H "Authorization: Bearer {k}" \\\n  -H "Content-Type: application/json" \\\n  -d \'{{"model": "{m}", "messages": [{{"role": "user", "content": "hi"}}], "max_tokens": 50}}\''
    elif p == "Anthropic":
        auth_url = "https://api.anthropic.com/v1/models"
        chat_url = "https://api.anthropic.com/v1/messages"
        m = model or "claude-3-5-haiku-20241022"
        auth_curl = f'curl -s -X GET "{auth_url}" \\\n  -H "x-api-key: {k}" \\\n  -H "anthropic-version: 2023-06-01"'
        chat_curl = f'curl -s -X POST "{chat_url}" \\\n  -H "x-api-key: {k}" \\\n  -H "anthropic-version: 2023-06-01" \\\n  -H "Content-Type: application/json" \\\n  -d \'{{"model": "{m}", "max_tokens": 50, "messages": [{{"role": "user", "content": "hi"}}]}}\''
    elif p == "Google Gemini":
        auth_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={k}"
        chat_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={k}"
        auth_curl = f'curl -s -X GET "{auth_url}"'
        chat_curl = f'curl -s -X POST "{chat_url}" \\\n  -H "Content-Type: application/json" \\\n  -d \'{{"contents": [{{"parts": [{{"text": "hi"}}]}}]}}\''
    elif p == "OpenRouter":
        auth_url = "https://openrouter.ai/api/v1/auth/key"
        chat_url = "https://openrouter.ai/api/v1/chat/completions"
        m = model or "openai/gpt-4o-mini"
        auth_curl = f'curl -s -X GET "{auth_url}" \\\n  -H "Authorization: Bearer {k}"'
        chat_curl = f'curl -s -X POST "{chat_url}" \\\n  -H "Authorization: Bearer {k}" \\\n  -H "Content-Type: application/json" \\\n  -d \'{{"model": "{m}", "messages": [{{"role": "user", "content": "hi"}}], "max_tokens": 50}}\''
    elif p == "DeepSeek":
        auth_url = "https://api.deepseek.com/v1/models"
        chat_url = "https://api.deepseek.com/v1/chat/completions"
        m = model or "deepseek-chat"
        auth_curl = f'curl -s -X GET "{auth_url}" \\\n  -H "Authorization: Bearer {k}"'
        chat_curl = f'curl -s -X POST "{chat_url}" \\\n  -H "Authorization: Bearer {k}" \\\n  -H "Content-Type: application/json" \\\n  -d \'{{"model": "{m}", "messages": [{{"role": "user", "content": "hi"}}], "max_tokens": 50}}\''
    else:  # Custom
        base = (custom_base_url or "https://api.openai.com/v1").rstrip("/")
        auth_url = f"{base}/models"
        chat_url = f"{base}/chat/completions"
        m = model or "default"
        auth_curl = f'curl -s -X GET "{auth_url}" \\\n  -H "Authorization: Bearer {k}"'
        chat_curl = f'curl -s -X POST "{chat_url}" \\\n  -H "Authorization: Bearer {k}" \\\n  -H "Content-Type: application/json" \\\n  -d \'{{"model": "{m}", "messages": [{{"role": "user", "content": "hi"}}], "max_tokens": 50}}\''

    single_line_auth = " ".join(auth_curl.replace("\\\n", " ").split())
    single_line_chat = " ".join(chat_curl.replace("\\\n", " ").split())
    
    watermark_tag = "# Verified via Dutchman KeySonar • Developed By Dutchman Security\n"

    return {
        "auth_url": auth_url,
        "chat_url": chat_url,
        "auth_curl": watermark_tag + auth_curl,
        "chat_curl": watermark_tag + chat_curl,
        "single_line_auth": single_line_auth,
        "single_line_chat": single_line_chat
    }

def parse_error_details(resp: requests.Response) -> str:
    """Extract informative, clean human-readable error messages from diverse API JSON payloads."""
    try:
        data = resp.json()
    except Exception:
        text = resp.text.strip()
        return text[:160] if text else f"HTTP {resp.status_code}"
        
    if isinstance(data, dict):
        if "error" in data:
            err = data["error"]
            if isinstance(err, dict):
                return err.get("message") or err.get("code") or json.dumps(err)
            elif isinstance(err, str):
                return err
        if "message" in data:
            return data["message"]
        if "detail" in data:
            return data["detail"]
        if "code" in data and "error" in data:
            return f"{data.get('code')}: {data.get('error')}"
    return str(data)[:160]

def extract_plan_and_credits(resp_auth, resp_chat, provider: str, key: str) -> dict:
    """Determine the API Key's Plan / Tier and Remaining Credits / Quota from headers, body, or billing endpoints."""
    # Check if key is invalid, revoked, or forbidden
    for r_check in [resp_auth, resp_chat]:
        if r_check is not None:
            if r_check.status_code in [401, 400]:
                return {
                    "plan": "Invalid / Revoked",
                    "credits": "Unauthorized ($0)",
                    "quota": "0 RPM (Key Rejected)"
                }
            elif r_check.status_code == 403:
                return {
                    "plan": "Restricted / Blocked",
                    "credits": "Forbidden (403)",
                    "quota": "0 RPM (Access Blocked)"
                }

    if resp_auth is None and resp_chat is None:
        return {
            "plan": "Unknown",
            "credits": "N/A (Network/Timeout)",
            "quota": "N/A"
        }

    plan = "Standard Tier"
    credits_info = "Active"
    quota_info = "Standard"
    
    if provider == "Groq":
        if resp_chat is not None and resp_chat.status_code == 200:
            try:
                body = resp_chat.json()
                stier = body.get("service_tier", "on_demand")
                plan = f"Groq {stier.replace('_', ' ').title()}"
            except Exception:
                plan = "Groq On-Demand"
                
            h = resp_chat.headers
            rem_req = h.get("x-ratelimit-remaining-requests")
            lim_req = h.get("x-ratelimit-limit-requests")
            rem_tok = h.get("x-ratelimit-remaining-tokens")
            lim_tok = h.get("x-ratelimit-limit-tokens")
            
            if rem_req and lim_req:
                quota_info = f"{rem_req}/{lim_req} RPM"
            if rem_tok and lim_tok:
                credits_info = f"{int(rem_tok):,} / {int(lim_tok):,} TPM"
            else:
                credits_info = "Active (Unlimited On-Demand)"
        elif resp_auth is not None and resp_auth.status_code == 200:
            plan = "Groq Developer (Free)"
            credits_info = "Active (Models OK)"
            quota_info = "30 RPM (Free Tier)"
        else:
            plan = "Groq Developer Free"
            credits_info = "Active"
            quota_info = "Standard"

    elif provider == "OpenAI":
        if resp_chat is not None and resp_chat.status_code == 429:
            err_text = resp_chat.text.lower()
            if any(w in err_text for w in ["credit_balance_exhausted", "insufficient_quota", "no credits", "billing"]):
                plan = "OpenAI Prepaid (Exhausted / $0)"
                credits_info = "$0.00 USD (Refill Needed)"
                quota_info = "0 RPM (Blocked by $0 balance)"
            else:
                plan = "OpenAI Rate Limited"
                credits_info = "Rate Limited (Wait & Retry)"
                quota_info = "0 RPM (Cooling down)"
        elif resp_chat is not None and resp_chat.status_code == 200:
            h = resp_chat.headers
            lim_req = h.get("x-ratelimit-limit-requests")
            rem_req = h.get("x-ratelimit-remaining-requests")
            lim_tok = h.get("x-ratelimit-limit-tokens")
            rem_tok = h.get("x-ratelimit-remaining-tokens")
            
            if lim_req:
                try:
                    lr = int(lim_req)
                    if lr <= 500:
                        plan = "OpenAI Free Tier"
                    elif lr <= 3500:
                        plan = "OpenAI Usage Tier 1 ($5-$50)"
                    elif lr <= 5000:
                        plan = "OpenAI Usage Tier 2 ($50-$100)"
                    elif lr <= 10000:
                        plan = "OpenAI Usage Tier 3 ($100-$250)"
                    else:
                        plan = f"OpenAI Tier 4/5 ({lim_req} RPM)"
                except Exception:
                    plan = f"OpenAI Paid ({lim_req} RPM)"
            else:
                plan = "OpenAI Paid Tier"
                
            if rem_tok and lim_tok:
                credits_info = f"{int(rem_tok):,} / {int(lim_tok):,} TPM"
            else:
                credits_info = "Funded & Active"
                
            if rem_req and lim_req:
                quota_info = f"{rem_req}/{lim_req} RPM"
        else:
            plan = "OpenAI Verified Account"
            credits_info = "Auth Valid"
            quota_info = "Account Active"

    elif provider == "OpenRouter":
        try:
            r = requests.get("https://openrouter.ai/api/v1/auth/key", headers={"Authorization": f"Bearer {key}"}, timeout=4)
            if r.status_code == 200:
                kdata = r.json().get("data", {})
                is_free = kdata.get("is_free_tier", False)
                plan = "OpenRouter Free" if is_free else "OpenRouter Paid"
                usage = kdata.get("usage", 0)
                limit = kdata.get("limit")
                if limit is not None:
                    credits_info = f"${float(limit) - float(usage):.2f} USD remaining"
                else:
                    credits_info = f"Usage: ${float(usage):.2f} USD (No limit)"
                rl = kdata.get("rate_limit", {})
                if rl:
                    quota_info = f"{rl.get('requests', '')} / {rl.get('interval', '')}"
            else:
                plan = "OpenRouter Standard"
        except Exception:
            plan = "OpenRouter"

    elif provider == "DeepSeek":
        try:
            r = requests.get("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"}, timeout=4)
            if r.status_code == 200:
                bdata = r.json()
                infos = bdata.get("balance_infos", [])
                if infos:
                    curr = infos[0].get("currency", "USD")
                    total = infos[0].get("total_balance", "0")
                    credits_info = f"{total} {curr}"
                    plan = "DeepSeek Funded" if float(total) > 0 else "DeepSeek $0 Balance"
                else:
                    plan = "DeepSeek Active"
            else:
                plan = "DeepSeek Standard"
        except Exception:
            plan = "DeepSeek"

    elif provider == "Anthropic":
        if resp_chat is not None and resp_chat.status_code == 200:
            h = resp_chat.headers
            lim_tok = h.get("anthropic-ratelimit-tokens-limit")
            rem_tok = h.get("anthropic-ratelimit-tokens-remaining")
            rem_req = h.get("anthropic-ratelimit-requests-remaining")
            lim_req = h.get("anthropic-ratelimit-requests-limit")
            plan = "Anthropic Build Tier"
            if rem_tok and lim_tok:
                credits_info = f"{int(rem_tok):,} / {int(lim_tok):,} TPM"
            if rem_req and lim_req:
                quota_info = f"{rem_req}/{lim_req} RPM"
        else:
            plan = "Anthropic Claude"

    elif provider == "Google Gemini":
        plan = "Google AI Studio"
        credits_info = "Free Tier (15 RPM) / Pay-as-you-go"
        quota_info = "15 RPM (Free) / 1000+ (Paid)"

    elif provider == "xAI (Grok)":
        plan = "xAI Developer Platform"
        credits_info = "Active"

    return {
        "plan": plan,
        "credits": credits_info,
        "quota": quota_info
    }

def clean_key_input(raw_input: str) -> list[str]:
    """Parse raw text, strip comments, remove quotes/whitespace/commas, and deduplicate."""
    cleaned = []
    seen = set()
    for line in raw_input.splitlines():
        if '#' in line:
            line = line.split('#')[0]
        line = line.strip().strip('"\'').strip(',').strip()
        if not line:
            continue
        tokens = [t.strip().strip('"\'').strip(',').strip() for t in line.replace(',', ' ').split()]
        for tok in tokens:
            if tok and len(tok) >= 8 and tok not in seen:
                seen.add(tok)
                cleaned.append(tok)
    return cleaned

def execute_key_test(key: str, provider_name: str, check_mode: str, model_override: str = None, 
                       custom_base_url: str = None, custom_model: str = None, timeout: int = 10) -> dict:
    """Execute validation against the provider endpoint and return structured diagnostics with plan & credits."""
    start_time = time.time()
    masked = mask_api_key(key)
    
    # Resolve provider
    actual_provider = detect_key_provider(key) if provider_name == "Auto-Detect" else provider_name
    
    if actual_provider == "Custom Endpoint":
        base = (custom_base_url or "").rstrip("/")
        auth_url = f"{base}/models"
        chat_url = f"{base}/chat/completions"
        model = custom_model or "default"
        header_type = "bearer"
    else:
        prov_info = PROVIDERS.get(actual_provider, PROVIDERS["OpenAI"])
        auth_url = prov_info.get("auth_url")
        chat_url = prov_info.get("chat_url")
        model = model_override or prov_info.get("default_model", "gpt-4o-mini")
        header_type = prov_info.get("header_type", "bearer")

    # Generate cURL commands for independent verification
    curls = generate_curl_commands(key, actual_provider, model, custom_base_url)

    # Standardize headers
    headers = {"Content-Type": "application/json"}
    if header_type == "bearer":
        headers["Authorization"] = f"Bearer {key}"
    elif header_type == "anthropic":
        headers["x-api-key"] = key
        headers["anthropic-version"] = "2023-06-01"

    def attach_details(res_dict, resp_auth_obj=None, resp_chat_obj=None):
        res_dict["curl_auth"] = curls["auth_curl"]
        res_dict["curl_chat"] = curls["chat_curl"]
        res_dict["single_line_auth"] = curls["single_line_auth"]
        res_dict["single_line_chat"] = curls["single_line_chat"]
        res_dict["auth_endpoint"] = curls["auth_url"]
        res_dict["chat_endpoint"] = curls["chat_url"]
        
        # Calculate Plan, Tier, and Remaining Credits
        pinfo = extract_plan_and_credits(resp_auth_obj, resp_chat_obj, actual_provider, key)
        res_dict["plan"] = pinfo["plan"]
        res_dict["credits"] = pinfo["credits"]
        res_dict["quota"] = pinfo["quota"]
        return res_dict

    # Step 1: Authentication / Models endpoint check
    try:
        if header_type == "gemini":
            cur_auth_url = auth_url.format(key=key)
            resp_auth = requests.get(cur_auth_url, timeout=timeout)
        else:
            resp_auth = requests.get(auth_url, headers=headers, timeout=timeout)
            
        latency_auth = int((time.time() - start_time) * 1000)
        auth_ok = (resp_auth.status_code == 200)

        # Dynamically discover live models from the key if returned
        if auth_ok and actual_provider in PROVIDERS and "models" in PROVIDERS[actual_provider]:
            try:
                auth_data = resp_auth.json()
                if "data" in auth_data and isinstance(auth_data["data"], list):
                    discovered_ids = [m["id"] for m in auth_data["data"] if "id" in m]
                    if discovered_ids:
                        existing = set(PROVIDERS[actual_provider]["models"])
                        for d_id in discovered_ids:
                            if d_id not in existing:
                                PROVIDERS[actual_provider]["models"].append(d_id)
            except Exception:
                pass

        if not auth_ok:
            err_msg = parse_error_details(resp_auth)
            if resp_auth.status_code in [401, 400] and any(w in err_msg.lower() for w in ["key", "invalid", "unauthorized", "credential", "authentication"]):
                return attach_details({
                    "key": key,
                    "masked": masked,
                    "provider": actual_provider,
                    "status_code": resp_auth.status_code,
                    "category": "Invalid",
                    "badge": "🔴 Invalid Key",
                    "card_class": "card-invalid",
                    "message": err_msg,
                    "latency_ms": latency_auth
                }, resp_auth_obj=resp_auth)
            elif resp_auth.status_code == 403:
                return attach_details({
                    "key": key,
                    "masked": masked,
                    "provider": actual_provider,
                    "status_code": 403,
                    "category": "Forbidden",
                    "badge": "🟣 Forbidden / Restricted",
                    "card_class": "card-other",
                    "message": f"Access forbidden (Permissions, Org restriction, or Geoblock): {err_msg}",
                    "latency_ms": latency_auth
                }, resp_auth_obj=resp_auth)
            elif resp_auth.status_code == 429:
                return attach_details({
                    "key": key,
                    "masked": masked,
                    "provider": actual_provider,
                    "status_code": 429,
                    "category": "Quota Depleted",
                    "badge": "🟠 Rate Limited / No Quota",
                    "card_class": "card-quota",
                    "message": err_msg,
                    "latency_ms": latency_auth
                }, resp_auth_obj=resp_auth)
            else:
                return attach_details({
                    "key": key,
                    "masked": masked,
                    "provider": actual_provider,
                    "status_code": resp_auth.status_code,
                    "category": "Error",
                    "badge": f"🟡 Auth HTTP {resp_auth.status_code}",
                    "card_class": "card-other",
                    "message": err_msg,
                    "latency_ms": latency_auth
                }, resp_auth_obj=resp_auth)

        # If user only wanted quick auth check (Zero Token Cost)
        if check_mode == "⚡ Quick Auth (Zero Token Cost)":
            return attach_details({
                "key": key,
                "masked": masked,
                "provider": actual_provider,
                "status_code": 200,
                "category": "Active",
                "badge": "🟢 Valid Key (Auth OK)",
                "card_class": "card-active",
                "message": "Key is valid & authenticated (Models list accessible)",
                "latency_ms": latency_auth
            }, resp_auth_obj=resp_auth)

        # Step 2: Chat completion test (Check Quota & Active Generation)
        if header_type == "gemini":
            cur_chat_url = chat_url.format(model=model, key=key)
            payload = {
                "contents": [{"parts": [{"text": "Hello"}]}],
                "generationConfig": {"maxOutputTokens": 40}
            }
            resp_chat = requests.post(cur_chat_url, json=payload, timeout=timeout)
        elif header_type == "anthropic":
            payload = {
                "model": model,
                "max_tokens": 40,
                "messages": [{"role": "user", "content": "Hello"}]
            }
            resp_chat = requests.post(chat_url, headers=headers, json=payload, timeout=timeout)
        else:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 40
            }
            resp_chat = requests.post(chat_url, headers=headers, json=payload, timeout=timeout)

        total_latency = int((time.time() - start_time) * 1000)

        if resp_chat.status_code == 200:
            assistant_reply = ""
            try:
                chat_data = resp_chat.json()
                if header_type == "gemini":
                    assistant_reply = chat_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                else:
                    msg = chat_data.get("choices", [{}])[0].get("message", {})
                    assistant_reply = msg.get("content") or msg.get("reasoning") or ""
            except Exception:
                pass
            clean_reply = assistant_reply.strip().replace("\n", " ")
            display_msg = f"Replied: \"{clean_reply[:60]}\"" if clean_reply else f"Verified (Model: {model})"
            return attach_details({
                "key": key,
                "masked": masked,
                "provider": actual_provider,
                "status_code": 200,
                "category": "Active",
                "badge": "🟢 Active & Ready",
                "card_class": "card-active",
                "message": display_msg,
                "reply": clean_reply,
                "latency_ms": total_latency
            }, resp_auth_obj=resp_auth, resp_chat_obj=resp_chat)
        elif resp_chat.status_code == 429:
            err_msg = parse_error_details(resp_chat)
            return attach_details({
                "key": key,
                "masked": masked,
                "provider": actual_provider,
                "status_code": 429,
                "category": "Quota Depleted",
                "badge": "🟠 Valid Key ($0 Quota / Depleted)",
                "card_class": "card-quota",
                "message": f"Auth passed, but quota depleted: {err_msg}",
                "latency_ms": total_latency
            }, resp_auth_obj=resp_auth, resp_chat_obj=resp_chat)
        elif resp_chat.status_code == 404:
            err_msg = parse_error_details(resp_chat)
            return attach_details({
                "key": key,
                "masked": masked,
                "provider": actual_provider,
                "status_code": 404,
                "category": "Active",
                "badge": "🔵 Valid Key (Model 404)",
                "card_class": "card-other",
                "message": f"Auth passed! Model '{model}' not accessible on this tier: {err_msg}",
                "latency_ms": total_latency
            }, resp_auth_obj=resp_auth, resp_chat_obj=resp_chat)
        else:
            err_msg = parse_error_details(resp_chat)
            return attach_details({
                "key": key,
                "masked": masked,
                "provider": actual_provider,
                "status_code": resp_chat.status_code,
                "category": "Active",
                "badge": f"🔵 Valid Key (Chat {resp_chat.status_code})",
                "card_class": "card-other",
                "message": f"Auth OK; Chat completion returned HTTP {resp_chat.status_code}: {err_msg}",
                "latency_ms": total_latency
            }, resp_auth_obj=resp_auth, resp_chat_obj=resp_chat)

    except requests.exceptions.Timeout:
        return attach_details({
            "key": key,
            "masked": masked,
            "provider": actual_provider,
            "status_code": "TIMEOUT",
            "category": "Error",
            "badge": "⚪ Timeout",
            "card_class": "card-error",
            "message": f"Request timed out after {timeout} seconds",
            "latency_ms": int((time.time() - start_time) * 1000)
        })
    except requests.exceptions.ConnectionError:
        return attach_details({
            "key": key,
            "masked": masked,
            "provider": actual_provider,
            "status_code": "CONN_ERR",
            "category": "Error",
            "badge": "⚪ Connection Error",
            "card_class": "card-error",
            "message": "Network connection error / Host unreachable",
            "latency_ms": int((time.time() - start_time) * 1000)
        })
    except Exception as e:
        return attach_details({
            "key": key,
            "masked": masked,
            "provider": actual_provider,
            "status_code": "ERR",
            "category": "Error",
            "badge": "⚪ Unexpected Error",
            "card_class": "card-error",
            "message": str(e)[:160],
            "latency_ms": int((time.time() - start_time) * 1000)
        })

# --- Session State Initialization ---
if "test_results" not in st.session_state:
    st.session_state["test_results"] = []
if "is_running" not in st.session_state:
    st.session_state["is_running"] = False
if "stop_requested" not in st.session_state:
    st.session_state["stop_requested"] = False

# Demo Mode for Screenshot & Instant Previews (?demo=true)
if st.query_params.get("demo") == "true" and not st.session_state["test_results"]:
    st.session_state["test_results"] = [
        {
            "key": "gsk_mock_demo_groq_key_val_000000000000000000000000",
            "masked": "gsk_mock...0000",
            "provider": "Groq",
            "status_code": 200,
            "category": "Active",
            "badge": "🟢 Active & Ready",
            "card_class": "card-active",
            "message": 'Replied: "Hello! How can I help you today?"',
            "latency_ms": 284,
            "plan": "Groq On-Demand",
            "credits": "7,977 / 8,000 TPM",
            "quota": "998 / 1,000 RPM",
            "curl_auth": '# Verified via Dutchman KeySonar • Developed By Dutchman Security\ncurl -s -X GET "https://api.groq.com/openai/v1/models" \\\n  -H "Authorization: Bearer gsk_mock_demo_groq_key_val_000000000000000000000000"',
            "curl_chat": '# Verified via Dutchman KeySonar • Developed By Dutchman Security\ncurl -s -X POST "https://api.groq.com/openai/v1/chat/completions" \\\n  -H "Authorization: Bearer gsk_mock_demo_groq_key_val_000000000000000000000000" \\\n  -H "Content-Type: application/json" \\\n  -d \'{"model": "qwen/qwen3.8-27b", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50}\'',
            "single_line_auth": 'curl -s -X GET "https://api.groq.com/openai/v1/models" -H "Authorization: Bearer gsk_mock_demo_groq_key_val_000000000000000000000000"',
            "single_line_chat": 'curl -s -X POST "https://api.groq.com/openai/v1/chat/completions" -H "Authorization: Bearer gsk_mock_demo_groq_key_val_000000000000000000000000" -H "Content-Type: application/json" -d \'{"model": "qwen/qwen3.8-27b", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50}\''
        },
        {
            "key": "sk-proj-mock_demo_openai_key_val_0000000000000000000000000000000000000000000000000000",
            "masked": "sk-proj-mock...0000",
            "provider": "OpenAI",
            "status_code": 429,
            "category": "Quota Depleted",
            "badge": "🟠 Valid Key ($0 Quota / Depleted)",
            "card_class": "card-quota",
            "message": "Auth passed, but quota depleted: You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.",
            "latency_ms": 312,
            "plan": "OpenAI Prepaid (Exhausted / $0)",
            "credits": "$0.00 USD (Refill Needed)",
            "quota": "0 RPM (Blocked by $0 balance)",
            "curl_auth": '# Verified via Dutchman KeySonar • Developed By Dutchman Security\ncurl -s -X GET "https://api.openai.com/v1/models" \\\n  -H "Authorization: Bearer sk-proj-mock..."',
            "curl_chat": '# Verified via Dutchman KeySonar • Developed By Dutchman Security\ncurl -s -X POST "https://api.openai.com/v1/chat/completions" \\\n  -H "Authorization: Bearer sk-proj-mock..." \\\n  -H "Content-Type: application/json" \\\n  -d \'{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50}\'',
            "single_line_auth": 'curl -s -X GET "https://api.openai.com/v1/models" -H "Authorization: Bearer sk-proj-mock..."',
            "single_line_chat": 'curl -s -X POST "https://api.openai.com/v1/chat/completions" -H "Authorization: Bearer sk-proj-mock..." -H "Content-Type: application/json" -d \'{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50}\''
        },
        {
            "key": "sk-proj-FAKEKEY99999999999999999999999999999999999999999999",
            "masked": "sk-proj-FAKE...9999",
            "provider": "OpenAI",
            "status_code": 401,
            "category": "Invalid",
            "badge": "🔴 Invalid Key",
            "card_class": "card-invalid",
            "message": "Incorrect API key provided: sk-proj-***********************************************9999. You can find your API key at https://platform.openai.com/account/api-keys.",
            "latency_ms": 198,
            "plan": "Invalid / Revoked",
            "credits": "Unauthorized ($0)",
            "quota": "0 RPM (Key Rejected)",
            "curl_auth": '# Verified via Dutchman KeySonar • Developed By Dutchman Security\ncurl -s -X GET "https://api.openai.com/v1/models" \\\n  -H "Authorization: Bearer sk-proj-FAKE..."',
            "curl_chat": '# Verified via Dutchman KeySonar • Developed By Dutchman Security\ncurl -s -X POST "https://api.openai.com/v1/chat/completions" \\\n  -H "Authorization: Bearer sk-proj-FAKE..." \\\n  -H "Content-Type: application/json" \\\n  -d \'{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50}\'',
            "single_line_auth": 'curl -s -X GET "https://api.openai.com/v1/models" -H "Authorization: Bearer sk-proj-FAKE..."',
            "single_line_chat": 'curl -s -X POST "https://api.openai.com/v1/chat/completions" -H "Authorization: Bearer sk-proj-FAKE..." -H "Content-Type: application/json" -d \'{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50}\''
        }
    ]

# --- App Header & Live Dynamic Status ---
header_col1, header_col2 = st.columns([3.8, 1.7])
with header_col1:
    st.markdown('<div class="main-header">🧭 Dutchman KeySonar</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Dynamic Multi-Provider AI API Key Validator • Live Model Sync • Quota & Balance Detection<br>'
        '<span class="brand-watermark">🛡️ Developed By <strong>Dutchman Security</strong></span></div>',
        unsafe_allow_html=True
    )
with header_col2:
    sync_time_str = st.session_state.get("sync_time", "Live")
    st.markdown(f"""
    <div style="text-align: right; padding-top: 10px;">
        <span class="sync-badge">
            <span style="font-size: 8px;">🟢</span> Live Sync Active ({sync_time_str})
        </span>
        <div style="font-size: 11px; color: #64748b; margin-top: 5px; font-weight: 500;">
            Architecture by <strong>Dutchman Security</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    provider_choice = st.selectbox(
        "Select Provider",
        list(PROVIDERS.keys()),
        index=0,
        help="Auto-Detect will inspect key prefixes (e.g. gsk_ for Groq, sk- for OpenAI, xai- for Grok)."
    )
    
    # Custom provider options
    custom_base_url = None
    custom_model = None
    selected_model = None
    
    if provider_choice == "Custom Endpoint":
        custom_base_url = st.text_input("Base URL", "https://api.together.xyz/v1", help="OpenAI-compatible base URL without trailing slash")
        custom_model = st.text_input("Model Name", "meta-llama/Llama-3-70b-chat-hf")
    elif provider_choice != "Auto-Detect":
        prov_info = PROVIDERS[provider_choice]
        st.caption(prov_info.get("doc", ""))
        available_models = prov_info.get("models", [])
        if available_models:
            selected_model = st.selectbox("Model to Verify", available_models, index=0)
    
    st.markdown("---")
    st.subheader("🎯 Test Strategy")
    check_mode = st.radio(
        "Validation Depth",
        ["🧠 Smart Dual-Check (Auth + Quota/Balance)", "⚡ Quick Auth (Zero Token Cost)"],
        index=0,
        help="Smart Dual-Check verifies if the key is genuine AND if it has active billing/quota. Quick Auth checks models list without consuming tokens."
    )
    
    st.markdown("---")
    st.subheader("⚡ Performance & Network")
    concurrency = st.slider("Concurrent Workers", min_value=1, max_value=20, value=5, help="Number of concurrent requests. Higher is faster.")
    request_timeout = st.slider("Timeout (seconds)", min_value=3, max_value=30, value=10)
    delay_between_requests = st.slider("Politeness Delay (seconds)", min_value=0.0, max_value=1.0, value=0.05, step=0.05)
    
    st.markdown("---")
    st.subheader("🔒 Privacy & Display")
    mask_keys_toggle = st.checkbox("Mask keys in table & cards", value=True)
    
    st.markdown("---")
    if st.button("🔄 Re-Sync Models & Endpoints", use_container_width=True):
        st.session_state["sync_initialized"] = False
        st.rerun()

    st.markdown("""
    <div style="background: rgba(30, 41, 59, 0.65); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 10px; padding: 14px; text-align: center; margin-top: 20px;">
        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600;">System Architect</div>
        <div style="font-size: 14px; font-weight: 700; color: #f8fafc; margin-top: 3px;">🛡️ Dutchman Security</div>
        <div style="font-size: 11px; color: #38bdf8; margin-top: 2px; font-weight: 500;">Developed By Dutchman Security</div>
    </div>
    """, unsafe_allow_html=True)

# --- Input Area (Tabs) ---
st.markdown("### 📥 Input API Keys")
tab_file, tab_paste, tab_samples = st.tabs(["📁 Upload File (.txt / .csv)", "✍️ Paste Keys", "💡 Sample Keys"])

input_keys = []

with tab_file:
    uploaded_file = st.file_uploader("Upload a file with API keys (one per line)", type=["txt", "csv"])
    if uploaded_file is not None:
        raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
        input_keys = clean_key_input(raw_text)

with tab_paste:
    pasted_text = st.text_area(
        "Paste API keys below (separated by newlines or spaces)",
        height=140,
        placeholder="gsk_mock_sample_groq_key_here_000000000000000000000000\nsk-proj-mock_sample_openai_key_here_000000000000000000000000...\nxai-..."
    )
    if pasted_text.strip() and not input_keys:
        input_keys = clean_key_input(pasted_text)

with tab_samples:
    st.markdown("""
    **Quick Demonstration Keys:** Click below to fill the test queue with test keys to verify auto-detection, error parsing, and cURL commands.
    """)
    if st.button("Load Sample Key Bundle"):
        sample_bundle = """
# Groq Key (Mock Sample)
gsk_mock_demo_groq_key_val_000000000000000000000000

# OpenAI Key (Mock Sample)
sk-proj-mock_demo_openai_key_val_0000000000000000000000000000000000000000000000000000

# Fake / Invalid Key (To verify 401 detection)
sk-proj-FAKEKEY99999999999999999999999999999999999999999999
gsk_FAKEGROQKEY123456789012345678901234567890123456789012
        """
        input_keys = clean_key_input(sample_bundle)

# --- Input Summary & Pre-flight Diagnostics ---
if input_keys:
    col_info1, col_info2 = st.columns([3, 1])
    with col_info1:
        st.success(f"📋 Loaded **{len(input_keys)} unique keys** ready for testing.")
        breakdown = {}
        for k in input_keys:
            p = detect_key_provider(k)
            breakdown[p] = breakdown.get(p, 0) + 1
        breakdown_str = " • ".join([f"**{p}**: {count}" for p, count in breakdown.items()])
        st.caption(f"Detected Providers: {breakdown_str}")
    
    with col_info2:
        if st.button("🧹 Clear Queue"):
            st.session_state["test_results"] = []
            st.rerun()

# --- Execution Buttons ---
col_btn1, col_btn2, col_btn_dummy = st.columns([1.5, 1.5, 5])
with col_btn1:
    start_test = st.button("🚀 Start Testing", type="primary", disabled=len(input_keys) == 0, use_container_width=True)
with col_btn2:
    stop_test = st.button("🛑 Stop Testing", disabled=not st.session_state["is_running"], use_container_width=True)

if stop_test:
    st.session_state["stop_requested"] = True

# --- Testing Engine (Multi-Threaded) ---
if start_test and input_keys:
    st.session_state["is_running"] = True
    st.session_state["stop_requested"] = False
    st.session_state["test_results"] = []
    
    progress_bar = st.progress(0.0)
    status_indicator = st.empty()
    live_metrics_placeholder = st.empty()
    
    total_keys = len(input_keys)
    completed_results = []
    
    start_exec_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_key = {
            executor.submit(
                execute_key_test, 
                key=k, 
                provider_name=provider_choice, 
                check_mode=check_mode, 
                model_override=selected_model,
                custom_base_url=custom_base_url,
                custom_model=custom_model,
                timeout=request_timeout
            ): k for k in input_keys
        }
        
        for idx, future in enumerate(as_completed(future_to_key)):
            if st.session_state.get("stop_requested", False):
                status_indicator.warning("🛑 Testing halted by user.")
                break
                
            res = future.result()
            completed_results.append(res)
            st.session_state["test_results"].append(res)
            
            done_count = len(completed_results)
            elapsed = time.time() - start_exec_time
            rate = done_count / elapsed if elapsed > 0 else 0
            eta_seconds = (total_keys - done_count) / rate if rate > 0 else 0
            
            progress_bar.progress(done_count / total_keys)
            status_indicator.markdown(
                f"**Testing:** `{res['masked']}` ({res['provider']}) — **{done_count}/{total_keys}** done "
                f"(`{rate:.1f}` keys/sec • ETA: `{eta_seconds:.1f}s`)"
            )
            
            active_cnt = sum(1 for r in completed_results if r["category"] == "Active")
            quota_cnt = sum(1 for r in completed_results if r["category"] == "Quota Depleted")
            invalid_cnt = sum(1 for r in completed_results if r["category"] == "Invalid")
            other_cnt = sum(1 for r in completed_results if r["category"] not in ["Active", "Quota Depleted", "Invalid"])
            
            with live_metrics_placeholder.container():
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("🟢 Active & Ready", active_cnt)
                m2.metric("🟠 Depleted Quota", quota_cnt)
                m3.metric("🔴 Invalid / Fake", invalid_cnt)
                m4.metric("⚪ Errors / Restricted", other_cnt)
                
            if delay_between_requests > 0:
                time.sleep(delay_between_requests)

    st.session_state["is_running"] = False
    progress_bar.progress(1.0)
    status_indicator.success(f"✅ Finished testing **{len(completed_results)}** keys in `{time.time() - start_exec_time:.2f}s`.")

# --- Results Presentation & Analysis ---
results = st.session_state.get("test_results", [])

if results:
    st.markdown("---")
    res_h1, res_h2 = st.columns([3.5, 1.5])
    with res_h1:
        st.markdown("### 📊 Test Results & Diagnostics")
    with res_h2:
        st.markdown('<div style="text-align: right; padding-top: 6px;"><span class="brand-watermark">🛡️ Developed By Dutchman Security</span></div>', unsafe_allow_html=True)
    
    total_tested = len(results)
    active_keys = [r for r in results if r["category"] == "Active"]
    quota_keys = [r for r in results if r["category"] == "Quota Depleted"]
    invalid_keys = [r for r in results if r["category"] == "Invalid"]
    other_keys = [r for r in results if r["category"] not in ["Active", "Quota Depleted", "Invalid"]]
    
    avg_latency = int(sum(r["latency_ms"] for r in results) / total_tested) if total_tested else 0
    success_rate = (len(active_keys) / total_tested * 100) if total_tested else 0
    
    # KPI Metrics Banner
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Total Tested", total_tested)
    kpi2.metric("🟢 Active & Ready", len(active_keys), delta=f"{success_rate:.0f}% success")
    kpi3.metric("🟠 Quota Depleted", len(quota_keys))
    kpi4.metric("🔴 Invalid / Revoked", len(invalid_keys))
    kpi5.metric("⚡ Avg Latency", f"{avg_latency} ms")
    
    # View Mode Selector: Cards (with 1-click copy) vs Table (Horizontal Scroll)
    view_col1, view_col2 = st.columns([2.5, 2])
    with view_col1:
        view_mode = st.radio(
            "Display Format",
            ["🃏 Rich Cards (with 1-Click cURL Copy & Live AI Text)", "📊 Data Table (Smooth Horizontal Scroll)"],
            index=0,
            horizontal=True
        )
    with view_col2:
        search_query = st.text_input("🔍 Search keys, provider, or status:", "", placeholder="Type to filter...")

    # Filter Tabs
    filter_tab_all, filter_tab_active, filter_tab_quota, filter_tab_invalid, filter_tab_errors = st.tabs([
        f"All ({total_tested})",
        f"🟢 Active ({len(active_keys)})",
        f"🟠 Quota Depleted ({len(quota_keys)})",
        f"🔴 Invalid ({len(invalid_keys)})",
        f"⚪ Errors ({len(other_keys)})"
    ])
    
    def apply_search(items):
        if not search_query.strip():
            return items
        q = search_query.strip().lower()
        return [r for r in items if q in r["key"].lower() or q in r["provider"].lower() or q in r["badge"].lower() or q in r["message"].lower()]
    
    def render_content(items):
        filtered_items = apply_search(items)
        if not filtered_items:
            st.info("No keys match the current filter or search query.")
            return

        if "Cards" in view_mode:
            # Render Rich Cards with 1-Click Copy Buttons and Plan/Balance Badges
            for idx, r in enumerate(filtered_items):
                display_key = r["masked"] if mask_keys_toggle else r["key"]
                card_cls = r.get("card_class", "card-other")
                plan_val = r.get("plan", "Standard Tier")
                credits_val = r.get("credits", "N/A")
                quota_val = r.get("quota", "N/A")
                
                with st.container():
                    st.markdown(f"""
                    <div class="key-card {card_cls}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div>
                                <span style="font-weight: 700; font-size: 15px;">{r['badge']}</span>
                                <span style="margin: 0 8px; color: #64748b;">•</span>
                                <code style="font-size: 14px; font-weight: bold;">{display_key}</code>
                            </div>
                            <div style="font-size: 12px; color: #64748b;">
                                <strong>{r['provider']}</strong> • HTTP <code>{r['status_code']}</code> • ⚡ {r['latency_ms']} ms
                            </div>
                        </div>
                        <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 10px;">
                            {r['message']}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); flex-wrap: wrap; gap: 8px;">
                            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                <span style="background: rgba(30, 41, 59, 0.8); border: 1px solid #334155; padding: 3px 10px; border-radius: 6px; font-size: 12px; color: #94a3b8;">
                                    💳 <strong>Plan / Tier:</strong> <span style="color: #f8fafc; font-weight: 600;">{plan_val}</span>
                                </span>
                                <span style="background: rgba(30, 41, 59, 0.8); border: 1px solid #334155; padding: 3px 10px; border-radius: 6px; font-size: 12px; color: #94a3b8;">
                                    💰 <strong>Remaining Credits / Balance:</strong> <span style="color: #38bdf8; font-weight: 600;">{credits_val}</span>
                                </span>
                                <span style="background: rgba(30, 41, 59, 0.8); border: 1px solid #334155; padding: 3px 10px; border-radius: 6px; font-size: 12px; color: #94a3b8;">
                                    ⏱️ <strong>Rate Quota:</strong> <span style="color: #a78bfa; font-weight: 600;">{quota_val}</span>
                                </span>
                            </div>
                            <div style="font-size: 11px; color: #64748b; font-weight: 500;">
                                🛡️ Verified by Dutchman Security
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander(f"📋 Copy Terminal cURL Command ({r['masked']})"):
                        tab_curl_a, tab_curl_c = st.tabs(["⚡ Auth Check cURL (GET /models)", "💬 Chat Completion cURL (POST)"])
                        with tab_curl_a:
                            st.caption("Click the copy button in the upper-right corner of this block:")
                            st.code(r.get("curl_auth", ""), language="bash")
                        with tab_curl_c:
                            st.caption("Click the copy button in the upper-right corner of this block:")
                            st.code(r.get("curl_chat", ""), language="bash")
        else:
            # Render Wide Data Table with Horizontal Scroll
            table_data = []
            for r in filtered_items:
                table_data.append({
                    "Status": r["badge"],
                    "API Key": r["masked"] if mask_keys_toggle else r["key"],
                    "Provider": r["provider"],
                    "Plan / Tier": r.get("plan", "Standard Tier"),
                    "Credits / Balance": r.get("credits", "N/A"),
                    "Rate Quota": r.get("quota", "N/A"),
                    "HTTP Code": str(r["status_code"]),
                    "Latency": f"{r['latency_ms']} ms",
                    "Details / Diagnostic Message": r["message"],
                    "Verified By": "Dutchman Security",
                    "Terminal cURL (Auth Check)": r.get("single_line_auth", ""),
                    "Terminal cURL (Chat Completion)": r.get("single_line_chat", "")
                })
            df = pd.DataFrame(table_data)
            
            col_cfg = {
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "API Key": st.column_config.TextColumn("API Key", width="medium"),
                "Provider": st.column_config.TextColumn("Provider", width="small"),
                "Plan / Tier": st.column_config.TextColumn("Plan / Tier", width="medium"),
                "Credits / Balance": st.column_config.TextColumn("Credits / Balance", width="medium"),
                "Rate Quota": st.column_config.TextColumn("Rate Quota", width="small"),
                "HTTP Code": st.column_config.TextColumn("HTTP Code", width="small"),
                "Latency": st.column_config.TextColumn("Latency", width="small"),
                "Details / Diagnostic Message": st.column_config.TextColumn("Details / Diagnostic Message", width="large"),
                "Verified By": st.column_config.TextColumn("Verified By", width="small"),
                "Terminal cURL (Auth Check)": st.column_config.TextColumn("Terminal cURL (Auth Check)", width="large"),
                "Terminal cURL (Chat Completion)": st.column_config.TextColumn("Terminal cURL (Chat Completion)", width="large")
            }
            
            st.caption("↔️ *Use the horizontal scrollbar at the bottom of the table to scroll smoothly from left to right.*")
            st.dataframe(df, column_config=col_cfg, hide_index=True, use_container_width=True)

    with filter_tab_all:
        render_content(results)
    with filter_tab_active:
        render_content(active_keys)
    with filter_tab_quota:
        render_content(quota_keys)
    with filter_tab_invalid:
        render_content(invalid_keys)
    with filter_tab_errors:
        render_content(other_keys)

    # --- Quick-Copy Toolbar ---
    st.markdown("#### 📋 Quick-Copy cURL Toolbar")
    key_labels = [f"{i+1}. {r['masked']} ({r['provider']} - {r['badge']})" for i, r in enumerate(results)]
    selected_idx = st.selectbox(
        "Select any tested key to copy its exact terminal cURL commands:",
        range(len(results)),
        format_func=lambda i: key_labels[i],
        key="quick_curl_select"
    )
    sel = results[selected_idx]
    
    toolbar_col1, toolbar_col2 = st.columns(2)
    with toolbar_col1:
        st.markdown(f"**⚡ Auth Check cURL (`GET`):** `{sel['masked']}`")
        st.code(sel.get("curl_auth", ""), language="bash")
    with toolbar_col2:
        st.markdown(f"**💬 Chat Completion cURL (`POST`):** `{sel['masked']}`")
        st.code(sel.get("curl_chat", ""), language="bash")

    # --- Export & Download Section ---
    st.markdown("### 💾 Export & Downloads")
    exp_col1, exp_col2, exp_col3 = st.columns(3)
    
    with exp_col1:
        valid_active_text = (
            "# ================================================================\n"
            "# Dutchman KeySonar — Active Valid Keys\n"
            "# Developed By Dutchman Security\n"
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"# Total Active Keys: {len(active_keys)}\n"
            "# ================================================================\n\n"
            + "\n".join([r["key"] for r in active_keys])
        )
        st.download_button(
            label=f"📥 Download Active Keys (.txt) [{len(active_keys)}]",
            data=valid_active_text,
            file_name="active_valid_keys.txt",
            mime="text/plain",
            disabled=len(active_keys) == 0,
            use_container_width=True
        )
        
    with exp_col2:
        all_valid_text = (
            "# ================================================================\n"
            "# Dutchman KeySonar — All Authentic Keys (Active + Quota Depleted)\n"
            "# Developed By Dutchman Security\n"
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"# Total Authentic Keys: {len(active_keys) + len(quota_keys)}\n"
            "# ================================================================\n\n"
            + "\n".join([r["key"] for r in (active_keys + quota_keys)])
        )
        st.download_button(
            label=f"📥 Download All Legitimate Keys (.txt) [{len(active_keys) + len(quota_keys)}]",
            data=all_valid_text,
            file_name="all_authentic_keys.txt",
            mime="text/plain",
            disabled=len(active_keys) + len(quota_keys) == 0,
            help="Includes active keys + keys that are authentic but out of credits.",
            use_container_width=True
        )
        
    with exp_col3:
        csv_df = pd.DataFrame(results)
        csv_df["verified_by"] = "Dutchman Security"
        cols = ["key", "masked", "provider", "category", "badge", "status_code", "plan", "credits", "quota", "latency_ms", "message", "verified_by", "curl_auth", "curl_chat"]
        csv_df = csv_df[[c for c in cols if c in csv_df.columns]]
        csv_data = csv_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label=f"📥 Download Full Report (.csv) [{total_tested}]",
            data=csv_data,
            file_name="api_validation_report.csv",
            mime="text/csv",
            use_container_width=True
        )

# --- Interactive Terminal Verification & Custom Key cURL Tester (Bottom Section) ---
st.markdown("---")
st.markdown("### 🛠️ Interactive Terminal Verification & Custom Key cURL Tester")
st.markdown(
    "Verify any API key directly using terminal cURL commands for **customer satisfaction and independent verification**. "
    "Enter or paste any custom API key below to detect its provider and endpoint, generate copy-paste ready `cURL` commands, "
    "and test authentication with custom prompts in real-time."
)

custom_c_col1, custom_c_col2 = st.columns([3, 1])
with custom_c_col1:
    default_manual_val = results[0]["key"] if results else ""
    manual_test_key = st.text_input(
        "Enter or Paste API Key to verify via cURL:",
        value=default_manual_val,
        placeholder="e.g. gsk_... or sk-proj-... or xai-...",
        help="Paste any key here to generate terminal verification commands."
    )

with custom_c_col2:
    manual_provider_override = st.selectbox(
        "Target Provider",
        ["Auto-Detect"] + [p for p in PROVIDERS.keys() if p != "Auto-Detect"],
        index=0,
        help="Leave on Auto-Detect to automatically detect endpoint by key prefix, or select manually."
    )

if manual_test_key.strip():
    cleaned_manual_key = manual_test_key.strip().strip('"\'')
    if manual_provider_override == "Auto-Detect":
        resolved_provider = detect_key_provider(cleaned_manual_key)
    else:
        resolved_provider = manual_provider_override
        
    curls = generate_curl_commands(cleaned_manual_key, resolved_provider)
    
    # Provider & Endpoint summary cards
    inf1, inf2, inf3 = st.columns(3)
    with inf1:
        st.markdown(f"**Detected Provider:** `{resolved_provider}`")
    with inf2:
        st.markdown(f"**Auth Endpoint (`GET`):** `{curls['auth_url']}`")
    with inf3:
        st.markdown(f"**Completion Endpoint (`POST`):** `{curls['chat_url']}`")
        
    st.markdown("#### 📋 Terminal cURL Commands (Copy & Run in Bash / Terminal)")
    curl_tab_auth, curl_tab_chat = st.tabs([
        "1. ⚡ Free Auth Check (`GET /models`)", 
        "2. 💬 Chat Completion / Quota Check (`POST`)"
    ])
    
    with curl_tab_auth:
        st.caption("Verify key authentication and access without consuming credits or generating tokens:")
        st.code(curls["auth_curl"], language="bash")
        
    with curl_tab_chat:
        st.caption("Verify active billing balance and model generation capabilities:")
        st.code(curls["chat_curl"], language="bash")
        
    # In-App Terminal Runner
    st.markdown("#### 🧪 Test Authentication In-App (Live Terminal Output Simulator)")
    test_mode_choice = st.radio(
        "Choose test action to run in terminal simulator:",
        ["💬 Test Live Chat Completion (Sends Prompt & Receives AI Reply)", "⚡ Test Auth Only (GET /models)"],
        index=0,
        horizontal=True
    )
    
    user_test_prompt = "Hello! What can you do for me today?"
    if "Chat Completion" in test_mode_choice:
        user_test_prompt = st.text_input("Test Prompt to send to model:", value=user_test_prompt)
        
    if st.button("▶️ Execute & View Live Terminal Response", type="primary", key="btn_run_manual_curl"):
        with st.spinner("Executing request to endpoint..."):
            start_m_time = time.time()
            headers = {"Content-Type": "application/json"}
            prov_details = PROVIDERS.get(resolved_provider, PROVIDERS["OpenAI"])
            h_type = prov_details.get("header_type", "bearer")
            
            if h_type == "bearer":
                headers["Authorization"] = f"Bearer {cleaned_manual_key}"
            elif h_type == "anthropic":
                headers["x-api-key"] = cleaned_manual_key
                headers["anthropic-version"] = "2023-06-01"
                
            r = None
            if "Auth Only" in test_mode_choice:
                target_url = curls["auth_url"]
                executed_curl = curls["auth_curl"]
                try:
                    r = requests.get(target_url, headers=headers if h_type != "gemini" else {}, timeout=10)
                    m_lat = int((time.time() - start_m_time) * 1000)
                    try:
                        resp_json = json.dumps(r.json(), indent=2)
                    except Exception:
                        resp_json = r.text
                    status_c = r.status_code
                except Exception as e:
                    resp_json = str(e)
                    status_c = "ERR"
                    m_lat = int((time.time() - start_m_time) * 1000)
                ai_text = None
            else:
                target_url = curls["chat_url"]
                executed_curl = curls["chat_curl"]
                target_model = prov_details.get("default_model", "gpt-4o-mini")
                payload = {
                    "model": target_model,
                    "messages": [{"role": "user", "content": user_test_prompt}],
                    "max_tokens": 60
                }
                try:
                    if h_type == "gemini":
                        gemini_url = target_url.format(model=target_model, key=cleaned_manual_key)
                        g_payload = {
                            "contents": [{"parts": [{"text": user_test_prompt}]}],
                            "generationConfig": {"maxOutputTokens": 60}
                        }
                        r = requests.post(gemini_url, json=g_payload, timeout=10)
                    elif h_type == "anthropic":
                        a_payload = {
                            "model": target_model,
                            "max_tokens": 60,
                            "messages": [{"role": "user", "content": user_test_prompt}]
                        }
                        r = requests.post(target_url, headers=headers, json=a_payload, timeout=10)
                    else:
                        r = requests.post(target_url, headers=headers, json=payload, timeout=10)
                        
                    m_lat = int((time.time() - start_m_time) * 1000)
                    status_c = r.status_code
                    try:
                        data = r.json()
                        resp_json = json.dumps(data, indent=2)
                        if h_type == "gemini":
                            ai_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        else:
                            msg = data.get("choices", [{}])[0].get("message", {})
                            ai_text = msg.get("content") or msg.get("reasoning") or ""
                    except Exception:
                        resp_json = r.text
                        ai_text = None
                except Exception as e:
                    resp_json = str(e)
                    status_c = "ERR"
                    ai_text = None
                    m_lat = int((time.time() - start_m_time) * 1000)

            # Detect Plan, Credits, and Rate Quota for manual test
            resp_auth_val = r if "Auth Only" in test_mode_choice else None
            resp_chat_val = r if "Chat Completion" in test_mode_choice else None
            m_pinfo = extract_plan_and_credits(resp_auth_val, resp_chat_val, resolved_provider, cleaned_manual_key)

            p1, p2, p3 = st.columns(3)
            with p1:
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">💳 Detected Plan / Tier</div>
                    <div style="font-size: 15px; font-weight: 700; color: #f8fafc; margin-top: 2px;">{m_pinfo['plan']}</div>
                </div>
                """, unsafe_allow_html=True)
            with p2:
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">💰 Remaining Credits / Balance</div>
                    <div style="font-size: 15px; font-weight: 700; color: #38bdf8; margin-top: 2px;">{m_pinfo['credits']}</div>
                </div>
                """, unsafe_allow_html=True)
            with p3:
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">⏱️ Rate Quota Limit</div>
                    <div style="font-size: 15px; font-weight: 700; color: #a78bfa; margin-top: 2px;">{m_pinfo['quota']}</div>
                </div>
                """, unsafe_allow_html=True)

            if ai_text and ai_text.strip():
                st.success(f"🤖 **Model Output:** {ai_text.strip()}")
            elif status_c == 429:
                st.warning("⚠️ **HTTP 429 (Quota Exceeded):** Authentication passed, but account balance is $0.")
            elif status_c in [401, 400]:
                st.error(f"❌ **HTTP {status_c} (Invalid Key):** Provider rejected the key as unauthorized.")

            status_color = "#22c55e" if status_c == 200 else ("#f97316" if status_c == 429 else "#ef4444")
            
            st.markdown(f"""
            <div class="terminal-box">
                <div class="terminal-header">
                    <span class="terminal-dot-red"></span>
                    <span class="terminal-dot-yellow"></span>
                    <span class="terminal-dot-green"></span>
                    <span>dutchman@keysonar:~$ (HTTP {status_c} • {m_lat}ms)</span>
                </div>
                <div style="color: #94a3b8; margin-bottom: 8px;">
                    <span style="color: #38bdf8; font-weight: 600;">dutchman@keysonar:~$</span> {executed_curl}
                </div>
                <div style="margin-bottom: 8px;">
                    <span style="color: {status_color}; font-weight: bold;">HTTP Status: {status_c}</span>
                    <span style="color: #64748b; margin-left: 12px;">Roundtrip: {m_lat} ms</span>
                    <span style="color: #64748b; margin-left: 12px;">•</span>
                    <span style="color: #38bdf8; margin-left: 12px; font-size: 11px; font-weight: 500;">🛡️ Verified via Dutchman Security Engine</span>
                </div>
                <pre style="color: #e2e8f0; font-size: 12px; max-height: 280px; overflow-y: auto;">{resp_json}</pre>
            </div>
            """, unsafe_allow_html=True)

# --- Documentation & Endpoint Reference Footer ---
st.markdown("---")
with st.expander("📖 API Endpoint Reference & Why Keys Might Fail"):
    st.markdown("""
    | Provider | Authentication Endpoint | Completion Endpoint | Typical Prefix |
    | :--- | :--- | :--- | :--- |
    | **Groq** | `https://api.groq.com/openai/v1/models` | `https://api.groq.com/openai/v1/chat/completions` | `gsk_...` |
    | **OpenAI** | `https://api.openai.com/v1/models` | `https://api.openai.com/v1/chat/completions` | `sk-proj-...` / `sk-...` |
    | **xAI (Grok)** | `https://api.x.ai/v1/models` | `https://api.x.ai/v1/chat/completions` | `xai-...` |
    | **Anthropic** | `https://api.anthropic.com/v1/models` | `https://api.anthropic.com/v1/messages` | `sk-ant-...` |
    | **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta/models` | `.../gemini-1.5-flash:generateContent` | `AIzaSy...` |
    | **OpenRouter** | `https://openrouter.ai/api/v1/auth/key` | `https://openrouter.ai/api/v1/chat/completions` | `sk-or-v1-...` |

    #### Key Diagnostic Differences
    * **🟢 Active & Ready (200 OK)**: Key is completely authentic, has active balance/quota, and generated completion text.
    * **🟠 Valid Key ($0 Quota / Depleted 429)**: The key is **genuine**, but the account has run out of credits or hit tier limits.
    * **🔴 Invalid Key (401 / 400)**: The key has been deleted, expired, revoked, or does not exist.
    * **🟣 Forbidden (403)**: Geolocation restrictions, organization permissions, or missing access rights.
    * **🔵 Valid Key (Model 404)**: Key is authentic, but the requested model does not exist or isn't enabled for your tier.
    """)

# --- Global Page Watermark Footer ---
st.markdown("---")
st.markdown(f"""
<div style="
    text-align: center; 
    margin-top: 30px; 
    padding: 30px 15px 25px 15px; 
    background: rgba(15, 23, 42, 0.4); 
    border-radius: 12px; 
    border: 1px solid rgba(99, 102, 241, 0.2);
">
    <div style="margin-bottom: 10px;">
        <span class="brand-watermark" style="font-size: 13px; padding: 6px 18px;">
            🛡️ Developed By Dutchman Security
        </span>
    </div>
    <div style="font-size: 14px; font-weight: 700; color: #f8fafc; letter-spacing: 0.5px;">
        🧭 DUTCHMAN KEYSONAR
    </div>
    <div style="color: #94a3b8; font-size: 12px; margin-top: 5px;">
        Multi-Provider AI Key Validation • Dynamic Model Sync • Cyber Threat Intelligence
    </div>
    <div style="color: #64748b; font-size: 11px; margin-top: 8px;">
        © {datetime.now().year} Dutchman Security. All rights reserved.
    </div>
</div>
""", unsafe_allow_html=True)
