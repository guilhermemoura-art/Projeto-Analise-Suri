import os
import sys
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CHATBOT_URL")
TOKEN    = os.getenv("API_TOKEN")
MSG_LIMIT    = 50
CONTACTS_CSV = "contacts.csv"
MESSAGES_CSV = "messages.csv"

if not BASE_URL or not TOKEN:
    sys.exit("Erro: CHATBOT_URL e API_TOKEN devem estar definidos no arquivo .env")

HEADERS = {
    "Accept":        "application/json",
    "Authorization": f"Bearer {TOKEN}",
}


def get_messages(user_id: str) -> list:
    try:
        response = requests.get(
            f"{BASE_URL}/api/contacts/{user_id}/messages",
            headers=HEADERS,
            params={"limit": MSG_LIMIT},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            print(f"  Aviso: resposta inesperada para {user_id}")
            return []
        return data.get("data", [])
    except requests.exceptions.ConnectionError:
        sys.exit(f"Erro: nao foi possivel conectar a {BASE_URL}. Verifique CHATBOT_URL no .env")
    except requests.exceptions.Timeout:
        sys.exit("Erro: a requisicao excedeu o tempo limite (30s)")
    except requests.exceptions.HTTPError as e:
        print(f"  Aviso HTTP {e.response.status_code} para {user_id}: ignorando.")
        return []


def fetch_messages_for_contacts(contact_ids: list) -> pd.DataFrame:
    all_messages = []
    total = len(contact_ids)

    for i, user_id in enumerate(contact_ids, start=1):
        print(f"[{i}/{total}] Buscando mensagens de {user_id}...")
        messages = get_messages(user_id)
        for msg in messages:
            msg["user_id"] = user_id
        all_messages.extend(messages)
        print(f"   {len(messages)} mensagens recebidas")

    return pd.DataFrame(all_messages)


if __name__ == "__main__":
    try:
        contacts_df = pd.read_csv(CONTACTS_CSV)
    except FileNotFoundError:
        sys.exit(f"Arquivo '{CONTACTS_CSV}' nao encontrado. Execute main.py primeiro.")

    contact_ids = contacts_df["id"].tolist()
    print(f"Total de contatos a processar: {len(contact_ids)}\n")

    df = fetch_messages_for_contacts(contact_ids)

    print(f"\nTotal de mensagens coletadas: {len(df)}")
    if not df.empty:
        print(f"Colunas: {df.columns.tolist()}")
        df.to_csv(MESSAGES_CSV, index=False)
        print(f"\nDados salvos em {MESSAGES_CSV}")
    else:
        print("Nenhuma mensagem coletada.")
