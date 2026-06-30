import os
import re
import sys
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

BASE_URL   = os.getenv("CHATBOT_URL", "").rstrip("/")
TOKEN      = os.getenv("API_TOKEN")
DATA_DIR   = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"
LIMIT        = 100
MSG_LIMIT    = 100
MAX_CONTACTS = 1000

HEADERS = {
    "Content-Type":  "application/json",
    "Accept":        "application/json",
    "Authorization": f"Bearer {TOKEN}",
}

_ISO_TRUNCATE = re.compile(r"(\.\d{6})\d+")


def _parse_iso(s: str) -> datetime:
    s = _ISO_TRUNCATE.sub(r"\1", s).replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def load_state() -> str | None:
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get("last_run")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(count: int) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(
            {
                "last_run": datetime.now(timezone.utc).isoformat(),
                "last_run_count": count,
            },
            f,
            indent=2,
        )


def _get_contacts_page(continuation_token: str = None) -> dict:
    body = {"limit": LIMIT, "orderBy": "lastActivity", "orderType": "desc"}
    if continuation_token:
        body["continuationToken"] = continuation_token
    try:
        r = requests.post(
            f"{BASE_URL}/api/contacts/list", headers=HEADERS, json=body, timeout=30
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        sys.exit(f"Erro: não foi possível conectar a {BASE_URL}.")
    except requests.exceptions.Timeout:
        sys.exit("Erro: timeout (30s) ao buscar contatos.")
    except requests.exceptions.HTTPError as e:
        sys.exit(f"Erro HTTP {e.response.status_code} ao buscar contatos.")


def _get_messages(user_id: str) -> list:
    headers = {k: v for k, v in HEADERS.items() if k != "Content-Type"}
    try:
        r = requests.get(
            f"{BASE_URL}/api/contacts/{user_id}/messages",
            headers=headers,
            params={"limit": MSG_LIMIT},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            return []
        return data.get("data", [])
    except requests.exceptions.ConnectionError:
        sys.exit(f"Erro: não foi possível conectar a {BASE_URL}.")
    except requests.exceptions.Timeout:
        sys.exit("Erro: timeout (30s) ao buscar mensagens.")
    except requests.exceptions.HTTPError as e:
        print(f"  Aviso HTTP {e.response.status_code} para {user_id}: ignorando.")
        return []


def fetch_incremental() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Busca contatos com lastActivity posterior à última execução (ou todos, na primeira vez).
    Retorna (contacts_df, messages_df).
    """
    if not BASE_URL or not TOKEN:
        sys.exit("Erro: CHATBOT_URL e API_TOKEN devem estar definidos no .env")

    last_run = load_state()
    last_run_dt = None
    if last_run:
        last_run_dt = _parse_iso(last_run)
        print(f"Fetch incremental desde {last_run}")
    else:
        print("Primeira execução: buscando todos os contatos.")

    all_contacts = []
    next_token   = None
    page         = 1
    stop         = False

    while not stop:
        print(f"Buscando página {page} de contatos...")
        data       = _get_contacts_page(next_token)
        items      = data.get("data", {}).get("items", [])
        next_token = data.get("data", {}).get("continuationToken")

        for item in items:
            if last_run_dt:
                activity = item.get("lastActivity") or item.get("lastMessageActivity")
                if activity:
                    try:
                        if _parse_iso(activity) <= last_run_dt:
                            stop = True
                            break
                    except (ValueError, TypeError):
                        pass
            all_contacts.append(item)
            if len(all_contacts) >= MAX_CONTACTS:
                stop = True
                break

        if not next_token:
            break
        page += 1

    contacts_df = pd.DataFrame(all_contacts)
    print(f"Contatos novos/atualizados: {len(contacts_df)}")

    if contacts_df.empty:
        return contacts_df, pd.DataFrame()

    all_messages = []
    contact_ids  = contacts_df["id"].tolist()
    total        = len(contact_ids)

    for i, user_id in enumerate(contact_ids, start=1):
        print(f"[{i}/{total}] Mensagens de {user_id}...")
        msgs = _get_messages(user_id)
        for m in msgs:
            m["user_id"] = user_id
        all_messages.extend(msgs)

    messages_df = pd.DataFrame(all_messages)
    print(f"Mensagens coletadas: {len(messages_df)}")
    return contacts_df, messages_df
