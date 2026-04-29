import sys
import pandas as pd

CSV_PATH = "contacts.csv"


def load_data(path: str = CSV_PATH) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        print(f"Arquivo carregado: {path}  ({len(df)} registros)\n")
        return df
    except FileNotFoundError:
        print(f"Arquivo '{path}' não encontrado. Execute main.py primeiro para gerar os dados.")
        sys.exit(1)


def visao_geral(df: pd.DataFrame) -> None:
    print("=" * 60)
    print("VISÃO GERAL")
    print("=" * 60)
    print(f"Linhas:   {df.shape[0]}")
    print(f"Colunas:  {df.shape[1]}")
    print(f"\nColunas disponíveis:\n  {df.columns.tolist()}\n")
    print("-- Tipos de dado ----------------------------")
    print(df.dtypes)
    print()


def valores_nulos(df: pd.DataFrame) -> None:
    print("=" * 60)
    print("VALORES NULOS")
    print("=" * 60)
    nulos = df.isnull().sum()
    pct   = (nulos / len(df) * 100).round(2)
    resumo = pd.DataFrame({"nulos": nulos, "% nulo": pct})
    print(resumo[resumo["nulos"] > 0].to_string() if resumo["nulos"].any() else "Nenhum valor nulo encontrado.")
    print()


def amostra(df: pd.DataFrame, n: int = 5) -> None:
    print("=" * 60)
    print(f"PRIMEIROS {n} REGISTROS")
    print("=" * 60)
    print(df.head(n).to_string())
    print()


def distribuicao_chatbot(df: pd.DataFrame) -> None:
    if "chatbotId" not in df.columns:
        return
    print("=" * 60)
    print("DISTRIBUIÇÃO POR CHATBOT")
    print("=" * 60)
    dist = df["chatbotId"].value_counts()
    print(dist.to_string())
    print(f"\nTotal de chatbots únicos: {dist.nunique()}\n")


def distribuicao_canal(df: pd.DataFrame) -> None:
    if "channelId" not in df.columns:
        return
    print("=" * 60)
    print("DISTRIBUIÇÃO POR CANAL")
    print("=" * 60)
    dist = df["channelId"].value_counts()
    print(dist.to_string())
    print(f"\nTotal de canais únicos: {dist.nunique()}\n")


def contatos_com_nome(df: pd.DataFrame) -> None:
    if "name" not in df.columns:
        return
    print("=" * 60)
    print("CONTATOS COM NOME PREENCHIDO")
    print("=" * 60)
    com_nome  = df["name"].notna().sum()
    sem_nome  = df["name"].isna().sum()
    print(f"Com nome:  {com_nome} ({com_nome / len(df) * 100:.1f}%)")
    print(f"Sem nome:  {sem_nome} ({sem_nome / len(df) * 100:.1f}%)\n")

    if com_nome > 0:
        print("Amostra de contatos com nome:")
        print(df[df["name"].notna()][["id", "name"]].head(10).to_string(index=False))
    print()


def estatisticas_descritivas(df: pd.DataFrame) -> None:
    numericas = df.select_dtypes(include="number")
    if numericas.empty:
        return
    print("=" * 60)
    print("ESTATÍSTICAS DESCRITIVAS (colunas numéricas)")
    print("=" * 60)
    print(numericas.describe().to_string())
    print()


def duplicatas(df: pd.DataFrame) -> None:
    print("=" * 60)
    print("DUPLICATAS")
    print("=" * 60)
    n_dup = df.duplicated().sum()
    print(f"Linhas duplicadas: {n_dup}")
    if "id" in df.columns:
        n_id_dup = df["id"].duplicated().sum()
        print(f"IDs duplicados:    {n_id_dup}")
    print()


if __name__ == "__main__":
    df = load_data()

    visao_geral(df)
    valores_nulos(df)
    amostra(df)
    contatos_com_nome(df)
    distribuicao_chatbot(df)
    distribuicao_canal(df)
    estatisticas_descritivas(df)
    duplicatas(df)

    print("=" * 60)
    print("Exploração concluída.")
