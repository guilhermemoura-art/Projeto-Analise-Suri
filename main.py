import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CHATBOT_URL")
TOKEN    = os.getenv("API_TOKEN")
LIMIT    = 15

HEADERS = {
    "Accept":        "application/json",
    "Authorization": f"Bearer {TOKEN}",
}


def get_contacts(continuation_token: str = None) -> dict:
    params = {"limit": LIMIT}
    if continuation_token:
        params["continuationToken"] = continuation_token

    response = requests.get(
        f"{BASE_URL}/api/contacts",
        headers=HEADERS,
        params=params,
    )
    response.raise_for_status()
    return response.json()


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

        items      = data["data"]["Items"]["data"]
        next_token = data["data"].get("ContinuationToken")

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

    print("── Primeiros registros ──────────────────────")
    print(df.head())

    print("\n── Tipos de dado ────────────────────────────")
    print(df.dtypes)

    print("\n── Valores nulos por coluna ─────────────────")
    print(df.isnull().sum())

    df.to_csv("contacts.csv", index=False)
    print("\nDados salvos em contacts.csv")
