import os
import sys
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CHATBOT_URL")
TOKEN    = os.getenv("API_TOKEN")
LIMIT    = 100

if not BASE_URL or not TOKEN:
    sys.exit("Erro: CHATBOT_URL e API_TOKEN devem estar definidos no arquivo .env")

HEADERS = {
    "Content-Type":  "application/json",
    "Accept":        "application/json",
    "Authorization": f"Bearer {TOKEN}",
}


def get_contacts(continuation_token: str = None) -> dict:
    body = {
        "limit":     LIMIT,
        "orderBy":   "lastActivity",
        "orderType": "desc",
    }
    if continuation_token:
        body["continuationToken"] = continuation_token

    try:
        response = requests.post(
            f"{BASE_URL}/api/contacts/list",
            headers=HEADERS,
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        sys.exit(f"Erro: não foi possível conectar a {BASE_URL}. Verifique CHATBOT_URL no .env")
    except requests.exceptions.Timeout:
        sys.exit("Erro: a requisição excedeu o tempo limite (30s)")
    except requests.exceptions.HTTPError as e:
        sys.exit(f"Erro HTTP {e.response.status_code}: {e.response.text}")


def fetch_all_contacts(max_pages: int = 5) -> pd.DataFrame:
    all_contacts = []
    next_token   = None
    page         = 1

    while page <= max_pages:
        print(f"Buscando página {page}...")
        data = get_contacts(next_token)

        if not data.get("success"):
            print("Resposta inesperada:", data)
            break

        items      = data.get("data", {}).get("items", [])
        next_token = data.get("data", {}).get("continuationToken")

        all_contacts.extend(items)
        print(f"   {len(items)} contatos recebidos")

        if not next_token:
            break

        page += 1

    return pd.DataFrame(all_contacts)


if __name__ == "__main__":
    df = fetch_all_contacts(max_pages=5)

    print(f"\nTotal de contatos: {len(df)}")
    print(f"Colunas disponíveis: {df.columns.tolist()}\n")

    print("-- Primeiros registros ----------------------")
    print(df.head())

    print("\n-- Tipos de dado ----------------------------")
    print(df.dtypes)

    print("\n-- Valores nulos por coluna -----------------")
    print(df.isnull().sum())

    df.to_csv("contacts.csv", index=False)
    print("\nDados salvos em contacts.csv")
