import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("Dashboard da Clínica")

# -----------------------------
# Conexão com Google Sheets
# -----------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# -----------------------------
# Carregar todas as abas existentes
# -----------------------------
abas_anos = ["2024", "2025", "2026"]
dfs = []

planilha = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1h5gdng8DNF8RVfknGnvRj-x2Vbx-ZeCrGhD_GKNuPFI"
)

abas_existentes = [ws.title for ws in planilha.worksheets()]

for aba in abas_anos:
    if aba in abas_existentes:
        sheet_aba = planilha.worksheet(aba)
        data_aba = sheet_aba.get_all_values()
        columns = [c if c.strip() != "" else f"Coluna_{i}" for i, c in enumerate(data_aba[0])]
        df_aba = pd.DataFrame(data_aba[1:], columns=columns)

        # Converter Valor Pago
        df_aba["Valor Pago"] = (
            df_aba["Valor Pago"]
            .astype(str)
            .str.replace("R$", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df_aba["Valor Pago"] = pd.to_numeric(df_aba["Valor Pago"], errors="coerce")
        df_aba = df_aba[df_aba["Valor Pago"].notna()]

        # Converter Atendimento
        df_aba["Atendimento"] = pd.to_datetime(
            df_aba["Atendimento"], dayfirst=False, errors="coerce"
        )

        dfs.append(df_aba)
    else:
        st.warning(f"Aba '{aba}' não encontrada na planilha!")

df_todos_anos = pd.concat(dfs, ignore_index=True)

# -----------------------------
# Criar coluna Ano corretamente
# -----------------------------
df_todos_anos["Ano"] = df_todos_anos["Atendimento"].dt.year
df_todos_anos["Ano"] = df_todos_anos["Ano"].astype("Int64")

# -----------------------------
# Filtro por ano
# -----------------------------
anos_disponiveis = sorted(df_todos_anos["Ano"].dropna().unique())

ano_selecionado = st.selectbox(
    "Escolher ano para análise",
    options=["Todos"] + [str(int(a)) for a in anos_disponiveis]
)

if ano_selecionado != "Todos":
    df_filtrado = df_todos_anos[df_todos_anos["Ano"] == int(ano_selecionado)]
else:
    df_filtrado = df_todos_anos.copy()

# -----------------------------
# Filtro de clientes
# -----------------------------
todos_clientes = df_filtrado["Nome do Cliente"].unique()

clientes_excluir = st.multiselect(
    "Selecionar clientes para excluir dos cálculos",
    options=todos_clientes
)

df_filtrado = df_filtrado[
    ~df_filtrado["Nome do Cliente"].isin(clientes_excluir)
]

# -----------------------------
# Métricas principais
# -----------------------------
faturamento_total = df_filtrado["Valor Pago"].sum()
ticket_medio = df_filtrado["Valor Pago"].mean()
pacientes = df_filtrado["Nome do Cliente"].nunique()
atendimentos = len(df_filtrado)

st.subheader("Métricas da clínica")

st.metric("Faturamento Total", f"R$ {faturamento_total:,.2f}")

col1, col2, col3 = st.columns(3)
col1.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
col2.metric("Pacientes", pacientes)
col3.metric("Sessões", atendimentos)

# -----------------------------
# NOVOS PACIENTES (CORREÇÃO AQUI)
# -----------------------------
primeiro_atendimento = (
    df_todos_anos.sort_values("Atendimento")
    .groupby("Nome do Cliente")["Atendimento"]
    .first()
    .reset_index()
)

primeiro_atendimento["Ano"] = primeiro_atendimento["Atendimento"].dt.year
primeiro_atendimento["Mes"] = primeiro_atendimento["Atendimento"].dt.to_period("M")

if ano_selecionado != "Todos":
    primeiro_atendimento = primeiro_atendimento[
        primeiro_atendimento["Ano"] == int(ano_selecionado)
    ]

novos_pacientes_mes = (
    primeiro_atendimento.groupby("Mes")
    .size()
    .reset_index(name="Novos Pacientes")
)

novos_pacientes_mes["Mes"] = novos_pacientes_mes["Mes"].astype(str)

# -----------------------------
# Faturamento mensal
# -----------------------------
df_filtrado["Mes"] = df_filtrado["Atendimento"].dt.strftime("%Y-%m")

faturamento_mes = (
    df_filtrado.groupby("Mes")["Valor Pago"]
    .sum()
    .reset_index()
)

# -----------------------------
# Gráficos lado a lado
# -----------------------------
col1, col2 = st.columns(2)

col1.subheader("Novos pacientes por mês")
col1.bar_chart(novos_pacientes_mes.set_index("Mes"))

col2.subheader("Faturamento mensal")
col2.bar_chart(faturamento_mes.set_index("Mes"))

# -----------------------------
# Último mês
# -----------------------------
if not novos_pacientes_mes.empty and not faturamento_mes.empty:
    col1, col2 = st.columns(2)
    col1.metric(
        "Novos pacientes no último mês",
        int(novos_pacientes_mes.iloc[-1]["Novos Pacientes"])
    )
    col2.metric(
        "Faturamento no último mês",
        f"R$ {faturamento_mes.iloc[-1]['Valor Pago']:,.2f}"
    )

# -----------------------------
# LTV por paciente
# -----------------------------
ltv_paciente = (
    df_filtrado.groupby("Nome do Cliente")["Valor Pago"]
    .sum()
    .reset_index()
    .rename(columns={"Valor Pago": "LTV"})
)

st.subheader("LTV por paciente")

col_table, col_kpis = st.columns([2, 1])

col_table.dataframe(ltv_paciente)

ltv_medio = ltv_paciente["LTV"].mean()
ltv_max = ltv_paciente["LTV"].max()
ltv_min = ltv_paciente["LTV"].min()

col_kpis.metric("LTV médio", f"R$ {ltv_medio:,.2f}")
col_kpis.metric("LTV máximo", f"R$ {ltv_max:,.2f}")
col_kpis.metric("LTV mínimo", f"R$ {ltv_min:,.2f}")

# -----------------------------
# Taxa de ocupação
# -----------------------------
capacidade_diaria = 6

periodo = st.selectbox(
    "Escolher período para a taxa de ocupação",
    options=["Diário", "Semanal", "Mensal"]
)

if periodo == "Diário":
    ocupacao = df_filtrado.groupby(
        df_filtrado["Atendimento"].dt.date
    )["Nome do Cliente"].count().reset_index()

    ocupacao.rename(
        columns={"Nome do Cliente": "Atendimentos"},
        inplace=True
    )

    ocupacao["Taxa (%)"] = (
        ocupacao["Atendimentos"] / capacidade_diaria
    ) * 100

    ocupacao = ocupacao.set_index("Atendimento")

elif periodo == "Semanal":
    ocupacao = df_filtrado.groupby(
        df_filtrado["Atendimento"].dt.to_period("W")
    ).agg(
        Atendimentos=("Nome do Cliente", "count"),
        Dias_Ativos=("Atendimento", "nunique")
    ).reset_index()

    ocupacao["Taxa (%)"] = (
        ocupacao["Atendimentos"] /
        (ocupacao["Dias_Ativos"] * capacidade_diaria)
    ) * 100

    ocupacao["Atendimento"] = ocupacao["Atendimento"].astype(str)
    ocupacao = ocupacao.set_index("Atendimento")

elif periodo == "Mensal":
    ocupacao = df_filtrado.groupby(
        df_filtrado["Atendimento"].dt.to_period("M")
    ).agg(
        Atendimentos=("Nome do Cliente", "count"),
        Dias_Ativos=("Atendimento", "nunique")
    ).reset_index()

    ocupacao["Taxa (%)"] = (
        ocupacao["Atendimentos"] /
        (ocupacao["Dias_Ativos"] * capacidade_diaria)
    ) * 100

    ocupacao["Atendimento"] = ocupacao["Atendimento"].astype(str)
    ocupacao = ocupacao.set_index("Atendimento")

st.subheader(f"Taxa de ocupação ({periodo})")
st.line_chart(ocupacao["Taxa (%)"])