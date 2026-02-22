import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def carregar_dados_marketing():

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )
    client = gspread.authorize(creds)

    planilha = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1k00rq893Sss2F2AXQn_K7_nixmVASte6RmphFDbwMEg"
    )

    sheet = planilha.sheet1

    df = pd.DataFrame(sheet.get_all_records())

    df.columns = df.columns.str.strip()

    return df

def custo_por_mes():
    df = carregar_dados_marketing()

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Custo"] = pd.to_numeric(df["Custo"], errors="coerce")

    df = df.dropna(subset=["Data"])
    df = df.sort_values("Data")

    # 👇 converter mês para datetime real
    df["Mes"] = df["Data"].dt.to_period("M").dt.to_timestamp()

    custo_mensal = (
        df.groupby("Mes")["Custo"]
        .sum()
        .reset_index()
    )

    return custo_mensal

def mostrar_marketing():

    st.header("📊 Marketing / Conversões")

    df = carregar_dados_marketing()

    # Conversões de tipo
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Conversões"] = pd.to_numeric(df["Conversões"], errors="coerce")
    df["Taxa de conv."] = pd.to_numeric(df["Taxa de conv."], errors="coerce")
    df["Custo"] = pd.to_numeric(df["Custo"], errors="coerce")

    # Remover linhas inválidas
    df = df.dropna(subset=["Data"])

    # Ordenar
    df = df.sort_values("Data")

    # Criar coluna de mês
    df = df.sort_values("Data")
    df = df.set_index("Data")

    # Criar indicador estratégico
    df["Custo por Conversão"] = df["Custo"] / df["Conversões"]

    # =============================
    # MÉTRICAS RESUMO
    # =============================

    total_conversoes = df["Conversões"].sum()
    total_custo = df["Custo"].sum()
    custo_medio = total_custo / total_conversoes if total_conversoes > 0 else 0

    col1, col2, col3 = st.columns(3)

    col1.metric("Total de Conversões", int(total_conversoes))
    col2.metric("Total Investido", f"R$ {total_custo:,.2f}")
    col3.metric("Custo Médio por Conversão", f"R$ {custo_medio:,.2f}")

    st.divider()

    # =============================
    # GRÁFICOS
    # =============================

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Conversões por mês")
        st.bar_chart(df["Conversões"])

    with col2:
        st.subheader("Custo por mês")
        st.bar_chart(df["Custo"])

    st.subheader("Custo por Conversão")
    st.line_chart(df["Custo por Conversão"])
