# Projeto Analise Suri
Uma ferramenta para analisar os problemas reportados pelos hóspedes em conversas via plataforma Suri.


# 📋 API de Contatos — Exploração com Python

Guia para consumir o endpoint `GET /api/contacts` com paginação e explorar os dados retornados.

---

## ⚙️ Requisitos

```bash
pip install requests pandas
```

---

## 🔧 Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
CHATBOT_URL=https://sua-url-aqui
API_TOKEN=seu-token-aqui
```

---

## 📦 Estrutura da Resposta

```json
{
  "success": true,
  "data": {
    "Items": {
      "data": [
        {
          "id": "wc1797:1819",
          "name": null,
          "chatbotId": "cb1797",
          "channelId": "wc1797"
        }
      ]
    },
    "ContinuationToken": "<token_para_proxima_pagina>"
  }
}
```

| Campo              | Tipo   | Descrição                        |
|--------------------|--------|----------------------------------|
| `Items`            | array  | Lista de contatos (Users)        |
| `ContinuationToken`| string | Token para buscar a próxima página |

---

## 🚀 Script Principal

```python
import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CHATBOT_URL")
TOKEN    = os.getenv("API_TOKEN")
LIMIT    = 15  # contatos por página

HEADERS = {
    "Accept":        "application/json",
    "Authorization": f"Bearer {TOKEN}",
}

def get_contacts(continuation_token: str = None) -> dict:
    """Busca uma página de contatos."""
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
    """Itera pelas páginas e consolida em DataFrame."""
    all_contacts   = []
    next_token     = None
    page           = 1

    while page <= max_pages:
        print(f"🔄 Buscando página {page}...")
        data = get_contacts(next_token)

        if not data.get("success"):
            print("❌ Resposta inesperada:", data)
            break

        items      = data["data"]["Items"]["data"]
        next_token = data["data"].get("ContinuationToken")

        all_contacts.extend(items)
        print(f"   ✅ {len(items)} contatos recebidos")

        if not next_token:  # sem mais páginas
            break

        page += 1

    return pd.DataFrame(all_contacts)


# ── Execução ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = fetch_all_contacts(max_pages=5)

    print(f"\n📊 Total de contatos: {len(df)}")
    print(f"📋 Colunas disponíveis: {df.columns.tolist()}\n")

    print("── Primeiros registros ──────────────────────")
    print(df.head())

    print("\n── Tipos de dado ────────────────────────────")
    print(df.dtypes)

    print("\n── Valores nulos por coluna ─────────────────")
    print(df.isnull().sum())

    # Exporta para análise posterior
    df.to_csv("contacts.csv", index=False)
    print("\n💾 Dados salvos em contacts.csv")
```

---

## 🔍 Explorando os Dados

Após rodar o script acima e gerar o `contacts.csv`, você pode continuar a análise:

```python
import pandas as pd

df = pd.read_csv("contacts.csv")

# Visão geral
df.info()
df.describe(include="all")

# Contatos com nome preenchido
df_com_nome = df[df["name"].notna()]

# Distribuição por chatbot
df.groupby("chatbotId").size().sort_values(ascending=False)

# Distribuição por canal
df.groupby("channelId").size().sort_values(ascending=False)
```

---

## 📄 Paginação

A API usa **cursor-based pagination**. O fluxo é:

```
1ª chamada  →  sem continuationToken  →  retorna Items + ContinuationToken
2ª chamada  →  continuationToken da resposta anterior  →  próxima página
...
Última página  →  ContinuationToken vazio ou ausente  →  fim
```

> ⚠️ O parâmetro `limit` **deve ser constante** em todas as chamadas de uma mesma sequência de paginação.

---

## 📁 Estrutura do Projeto

```
.
├── .env              # Credenciais (não versionar)
├── .gitignore
├── README.md
├── main.py           # Script principal
├── contacts.csv      # Gerado após execução
└── requirements.txt
```

### `requirements.txt`

```
requests
pandas
python-dotenv
```

### `.gitignore`

```
.env
contacts.csv
__pycache__/
*.pyc
```

---

## ▶️ Como Rodar

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar
python main.py
```
