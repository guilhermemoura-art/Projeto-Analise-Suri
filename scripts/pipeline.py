import sys
import json
import math
from pathlib import Path
from datetime import datetime

from fetch import fetch_incremental, save_state

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
from filter_messages import filter_automated
from lgpd import anonymize
from classify import classify_problems

def _clean(v):
    """Converte NaN/NA para None antes de serializar em JSON."""
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def run() -> None:
    print(f"\n=== Pipeline Suri — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    # 1. Fetch incremental
    contacts_df, messages_df = fetch_incremental()

    if contacts_df.empty:
        print("Nenhum dado novo desde a última execução. Encerrando.")
        save_state(0)
        return

    # 2. Filtrar mensagens automáticas
    messages_df = filter_automated(messages_df)

    if messages_df.empty:
        print("Nenhuma mensagem relevante encontrada após filtragem.")
        save_state(len(contacts_df))
        return

    # 3. Anonimizar PII (LGPD)
    contacts_df, messages_df = anonymize(contacts_df, messages_df)

    # 4. Classificar com Google GenAI
    messages_df = classify_problems(messages_df)

    # 5. Mesclar nome do hóspede (identificador WhatsApp)
    if "name" in contacts_df.columns and "contact_key" in contacts_df.columns:
        name_map = contacts_df.set_index("contact_key")["name"].to_dict()
        messages_df["name"] = messages_df["contact_key"].map(name_map)

    # 6. Exportar apenas conversas com problemas identificados
    problems_df = messages_df[messages_df["has_problem"] == True].copy()
    date_str    = datetime.now().strftime("%Y-%m-%d")
    output_path = DATA_DIR / f"messages_processed_{date_str}.json"

    if problems_df.empty:
        print("Nenhum problema identificado nesta execução.")
    else:
        records = []
        for contact_key, group in problems_df.groupby("contact_key"):
            first = group.iloc[0]
            msgs = [
                {
                    "createdAt": _clean(row["createdAt"]),
                    "type":      _clean(row.get("type")),
                    "text":      _clean(row.get("text")),
                }
                for _, row in group.sort_values("createdAt").iterrows()
            ]
            records.append({
                "contact_key":      contact_key,
                "name":             _clean(first.get("name")),
                "has_problem":      bool(first["has_problem"]),
                "problem_summary":  _clean(first.get("problem_summary")),
                "problem_category": _clean(first.get("problem_category")),
                "severity":         _clean(first.get("severity")),
                "messages":         msgs,
            })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        print(f"\nResultado salvo em: {output_path}")
        print(f"  Conversas com problemas : {len(records)}")
        print(f"  Total de mensagens      : {len(problems_df)}")
        if records:
            from collections import Counter
            cats = Counter(r["problem_category"] for r in records if r["problem_category"])
            print(f"\nDistribuição por categoria:")
            for cat, count in cats.most_common():
                print(f"  {cat}: {count}")

    # 7. Atualizar state.json após conclusão bem-sucedida
    save_state(len(contacts_df))
    print("\nPipeline concluído com sucesso.")


if __name__ == "__main__":
    run()
