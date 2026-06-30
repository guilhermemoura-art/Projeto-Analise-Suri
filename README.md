# Projeto Análise Suri

Pipeline automatizado para identificar problemas relatados por hóspedes em conversas via plataforma **Suri/Tactu**. Coleta mensagens do chatbot, filtra automações, anonimiza dados sensíveis (LGPD) e classifica conversas com Google Gemini.

---

## Fluxo do Pipeline

```
API Suri
   │
   ▼
fetch.py          ← busca incremental (até 1000 contatos desde last_run)
   │
   ▼
filter_messages.py ← remove SystemMessages e AgentMessages automáticas (~85 padrões)
   │
   ▼
lgpd.py           ← remove CPF, telefone, e-mail; SHA-256 no ID; preserva nome WhatsApp
   │
   ▼
classify.py       ← envia batches de 25 conversas ao Gemini, retorna JSON estruturado
   │
   ▼
data/messages_processed_YYYY-MM-DD.json
```

---

## Estrutura do Projeto

```
.
├── scripts/
│   ├── pipeline.py         # Orquestrador principal
│   ├── fetch.py            # Coleta incremental da API
│   ├── filter_messages.py  # Filtro de mensagens automáticas
│   ├── lgpd.py             # Anonimização de PII
│   ├── classify.py         # Classificação com Google Gemini
│   └── dag_suri.py         # DAG para Airflow (execução semanal)
├── data/
│   ├── state.json          # Controle de execução incremental (não versionar)
│   └── messages_processed_YYYY-MM-DD.json  # Output (não versionar)
├── .env                    # Credenciais (não versionar)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Configuração

### 1. Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

```env
CHATBOT_URL=https://seu-endpoint.azurewebsites.net/
API_TOKEN=seu_token_aqui
GOOGLE_API_KEY=sua_chave_aqui
```

### 2. Instalar dependências

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

---

## Como Rodar

```bash
python scripts/pipeline.py
```

Na primeira execução (sem `data/state.json`), busca os 1000 contatos mais recentes. Nas execuções seguintes, busca apenas os contatos com atividade posterior ao último run.

Para reprocessar o lote anterior, edite `data/state.json` e retroceda o campo `last_run`.

---

## Output

Arquivo `data/messages_processed_YYYY-MM-DD.json` — array de conversas com problema identificado:

```json
[
  {
    "contact_key": "e181cd24ef6b6447",
    "name": "Nome do Hóspede",
    "has_problem": true,
    "problem_summary": "Hóspede não conseguiu incluir 2 pessoas adicionais no check-in.",
    "problem_category": "check-in",
    "severity": 2.0,
    "messages": [
      { "createdAt": 1782839426978, "type": "AgentMessage", "text": "Cadastrados, basta se apresentar..." },
      { "createdAt": 1782839461349, "type": "UserMessage",  "text": "Obrigada, Iago" }
    ]
  }
]
```

### Campos de classificação

| Campo | Tipo | Descrição |
|---|---|---|
| `has_problem` | bool | Hóspede relatou problema real no imóvel/reserva |
| `problem_summary` | string | Resumo objetivo em português (máx. 200 chars) |
| `problem_category` | string | `check-in` · `limpeza` · `manutenção` · `comunicação` · `cancelamento` · `pagamento` · `outro` |
| `severity` | int 1–5 | 1 = leve, 5 = crítico |

---

## Conformidade LGPD

- **IDs de contato** (contêm número de telefone na API) são substituídos por hash SHA-256 de 16 chars (`contact_key`).
- **CPF**, **telefone** e **e-mail** são redatados do texto das mensagens (`[CPF REMOVIDO]`, `[TELEFONE REMOVIDO]`, `[EMAIL REMOVIDO]`).
- **Identificador preservado**: apenas o nome do WhatsApp (`name`).
- Colunas removidas: `phone`, `email`, `identificationDocument`, `profilePicture`, `note`, `user_id`, `senderId`, `conversationId`.

---

## Parâmetros Configuráveis

Em `scripts/fetch.py`:
```python
MAX_CONTACTS = 1000   # máximo de contatos por execução
LIMIT        = 100    # contatos por página da API
MSG_LIMIT    = 100    # mensagens por contato
```

Em `scripts/classify.py`:
```python
BATCH_SIZE          = 25    # conversas por chamada Gemini
# defaults de classify_problems():
model               = "gemini-3.1-flash-lite"
requests_per_minute = 12    # respeitando limite de 15 RPM do tier gratuito
```

---

## Agendamento com Airflow

`scripts/dag_suri.py` define uma DAG que executa o pipeline toda segunda-feira às 8h:

```python
schedule_interval = "0 8 * * 1"
```

Para usar no Airflow, copie `dag_suri.py` para a pasta `dags/` do seu ambiente e certifique-se de que o diretório `scripts/` está acessível no `PYTHONPATH`.

---

## Dependências

```
requests
pandas
python-dotenv
google-genai
```
