import re
import hashlib
import pandas as pd

# CPF formatado (XXX.XXX.XXX-XX) — padrão de alta confiança
CPF_FORMATTED   = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
# CPF com contexto explícito ("CPF: 12345678901")
CPF_WITH_LABEL  = re.compile(r"(?i)(cpf\s*[:\-]?\s*)(\d{3}\.?\d{3}\.?\d{3}-?\d{2})")
# Telefone brasileiro (fixo e celular), formatos comuns em mensagens de texto
PHONE_PATTERN   = re.compile(
    r"(\+?55[\s\-.]?)?\(?\b[1-9]\d\)?[\s\-.]?9?\d{4}[\s\-.]?\d{4}\b"
)
# E-mail
EMAIL_PATTERN   = re.compile(r"[\w.+\-]+@[\w\-]+\.[a-z]{2,}", re.IGNORECASE)

CONTACT_DROP_COLS = [
    "phone",
    "email",
    "identificationDocument",
    "profilePicture",
    "note",
]
MESSAGE_DROP_COLS = ["user_id", "senderId", "conversationId"]


def _hash_id(raw_id: str) -> str:
    if not isinstance(raw_id, str) or not raw_id:
        return "unknown"
    return hashlib.sha256(raw_id.encode()).hexdigest()[:16]


def _redact_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = CPF_WITH_LABEL.sub(r"\1[CPF_REDACTED]", text)
    text = CPF_FORMATTED.sub("[CPF_REDACTED]", text)
    text = PHONE_PATTERN.sub("[TEL_REDACTED]", text)
    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    return text


def _count_cpf(series: pd.Series) -> int:
    return series.dropna().apply(lambda t: bool(CPF_FORMATTED.search(str(t)))).sum()


def anonymize(
    contacts_df: pd.DataFrame,
    messages_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Remove/substitui todos os dados pessoais identificáveis conforme LGPD.

    Contatos:
      - Gera contact_key (SHA-256 do id, primeiros 16 hex) como surrogate key
      - Remove: phone, email, identificationDocument, profilePicture, note, id

    Mensagens:
      - Substitui CPF, telefone e e-mail no campo text por marcadores [REDACTED]
      - Remove: user_id, senderId, conversationId (contêm telefone no formato da API)
      - Mapeia user_id → contact_key para manter vínculo sem expor PII

    Retorna (contacts_df_anonimizado, messages_df_anonimizado).
    """
    # --- Contatos ---
    contacts = contacts_df.copy()
    contacts["contact_key"] = contacts["id"].apply(_hash_id)

    drop_contacts = [c for c in CONTACT_DROP_COLS + ["id"] if c in contacts.columns]
    contacts = contacts.drop(columns=drop_contacts)

    first_cols = ["contact_key", "name"]
    rest_cols  = [c for c in contacts.columns if c not in first_cols]
    contacts   = contacts[[c for c in first_cols if c in contacts.columns] + rest_cols]

    # --- Mensagens ---
    if messages_df.empty:
        return contacts, messages_df

    messages = messages_df.copy()

    id_to_key = dict(zip(contacts_df["id"], contacts["contact_key"]))
    messages["contact_key"] = messages["user_id"].map(id_to_key)

    cpf_before = _count_cpf(messages["text"])
    messages["text"] = messages["text"].apply(_redact_text)
    cpf_after  = _count_cpf(messages["text"])

    drop_msgs = [c for c in MESSAGE_DROP_COLS if c in messages.columns]
    messages  = messages.drop(columns=drop_msgs)

    print(
        f"LGPD: CPFs no texto antes={cpf_before}, depois={cpf_after}. "
        f"Colunas removidas: {drop_contacts + drop_msgs}"
    )
    return contacts, messages
