import os
import re
import json
import time
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE = 25

BATCH_PROMPT_TEMPLATE = """\
Você é um analista de experiência do hóspede. Analise as {n} conversas abaixo entre hóspedes e a plataforma de atendimento de uma hospedagem.

Para CADA conversa, retorne um objeto no array JSON com os campos:
- "conversa_id": número da conversa conforme indicado no separador (inteiro)
- "has_problem": true ou false — se o hóspede relatou algum problema real na reserva ou no imóvel
- "problem_summary": resumo objetivo do problema em português, máx 200 chars (null se has_problem=false)
- "problem_category": uma de ["check-in", "limpeza", "manutenção", "comunicação", "cancelamento", "pagamento", "outro"] (null se has_problem=false)
- "severity": inteiro de 1 a 5 — 1=leve, 5=crítico (null se has_problem=false)

Ignore reclamações sobre o processo automatizado do chatbot (links, formulários, etc.).
Foque apenas em problemas reais que o hóspede enfrentou com o imóvel ou a reserva.

Responda APENAS com o array JSON válido, sem texto adicional.

{conversations_block}"""

_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*?\]", re.DOTALL)
_EMPTY = {"has_problem": False, "problem_summary": None, "problem_category": None, "severity": None}


def _build_conversation(group: pd.DataFrame) -> str:
    lines = []
    for _, row in group.sort_values("createdAt").iterrows():
        role = "Hóspede" if row.get("type") == "UserMessage" else "Atendimento"
        text = str(row.get("text") or "").strip()
        if text and text != "nan":
            lines.append(f"[{role}]: {text}")
    return "\n".join(lines)


def _build_batch_block(indexed_groups: list) -> str:
    parts = []
    for idx, conv_text in indexed_groups:
        parts.append(f"=== CONVERSA {idx} ===\n{conv_text}")
    return "\n\n".join(parts)


def _parse_batch_response(raw: str, batch_ids: list) -> dict:
    match = _JSON_ARRAY_RE.search(raw)
    if not match:
        return {i: _EMPTY.copy() for i in batch_ids}
    try:
        items = json.loads(match.group())
        result = {}
        for item in items:
            if "conversa_id" not in item:
                continue
            result[item["conversa_id"]] = {
                "has_problem":      bool(item.get("has_problem", False)),
                "problem_summary":  item.get("problem_summary"),
                "problem_category": item.get("problem_category"),
                "severity":         item.get("severity"),
            }
        for i in batch_ids:
            if i not in result:
                result[i] = _EMPTY.copy()
        return result
    except (json.JSONDecodeError, KeyError):
        return {i: _EMPTY.copy() for i in batch_ids}


def _handle_retry(e: Exception, attempt: int, max_retries: int) -> bool:
    """Retorna True se deve tentar novamente; levanta exceção se deve abortar."""
    msg = str(e)
    if "404" in msg or "NOT_FOUND" in msg:
        raise
    if "limit: 0" in msg:
        print(
            "\n  ERRO PERMANENTE: o modelo não tem quota neste projeto (limit: 0).\n"
            "  Verifique se o modelo está disponível na sua chave em: https://aistudio.google.com"
        )
        raise
    if any(kw in msg.lower() for kw in ("billing", "check your plan", "per day", "daily limit")):
        raise
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        if attempt < max_retries - 1:
            wait = 60 * (attempt + 1)
            print(f"  Rate limit atingido. Aguardando {wait}s (tentativa {attempt + 1}/{max_retries - 1})...")
            time.sleep(wait)
            return True
        raise
    raise


def _classify_batch(client, model: str, indexed_groups: list, max_retries: int = 3) -> dict:
    """Classifica um batch de conversas em uma única chamada. Retorna {conversa_id: resultado}."""
    batch_ids = [idx for idx, _ in indexed_groups]
    conversations_block = _build_batch_block(indexed_groups)
    prompt = BATCH_PROMPT_TEMPLATE.format(n=len(indexed_groups), conversations_block=conversations_block)

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return _parse_batch_response(response.text.strip(), batch_ids)
        except Exception as e:
            try:
                if _handle_retry(e, attempt, max_retries):
                    continue
            except Exception as abort_e:
                print(f"  Aviso: erro no batch — {abort_e}")
                return {i: _EMPTY.copy() for i in batch_ids}
    return {i: _EMPTY.copy() for i in batch_ids}


def classify_problems(
    messages_df: pd.DataFrame,
    model: str = "gemini-3.1-flash-lite",
    requests_per_minute: int = 12,
) -> pd.DataFrame:
    """
    Agrupa mensagens por contact_key e classifica em batches de BATCH_SIZE conversas
    por chamada Gemini. Adiciona colunas: has_problem, problem_summary, problem_category, severity.
    """
    from google import genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY não definido no .env")

    client = genai.Client(api_key=api_key)

    if messages_df.empty or "contact_key" not in messages_df.columns:
        for col in ["has_problem", "problem_summary", "problem_category", "severity"]:
            messages_df[col] = None
        return messages_df

    delay = 60.0 / requests_per_minute
    groups = list(messages_df.groupby("contact_key"))
    indexed = [(i + 1, ck, grp) for i, (ck, grp) in enumerate(groups)]
    total_batches = (len(indexed) + BATCH_SIZE - 1) // BATCH_SIZE

    results = {}

    for batch_num, batch_start in enumerate(range(0, len(indexed), BATCH_SIZE), start=1):
        batch = indexed[batch_start:batch_start + BATCH_SIZE]
        batch_for_api = [(idx, _build_conversation(grp)) for idx, ck, grp in batch]
        batch_map     = {idx: ck for idx, ck, grp in batch}

        print(f"Batch {batch_num}/{total_batches}: classificando {len(batch)} conversas...")
        batch_results = _classify_batch(client, model, batch_for_api)

        for idx, result in batch_results.items():
            results[batch_map[idx]] = result

        if batch_start + BATCH_SIZE < len(indexed):
            time.sleep(delay)

    results_df = pd.DataFrame([{"contact_key": ck, **res} for ck, res in results.items()])
    merged = messages_df.merge(results_df, on="contact_key", how="left")

    problem_count = int(results_df["has_problem"].sum())
    print(f"Classificação concluída: {problem_count}/{len(groups)} conversas com problemas identificados.")
    return merged
