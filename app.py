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

sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1h5gdng8DNF8RVfknGnvRj-x2Vbx-ZeCrGhD_GKNuPFI"
).sheet1

data = sheet.get_all_records()
df = pd.DataFrame(data)

# -----------------------------
# Filtro de clientes
# -----------------------------
todos_clientes = df["Nome do Cliente"].unique()
clientes_excluir = st.multiselect(
    "Selecionar clientes para **excluir** dos cálculos",
    options=todos_clientes
)
df_filtrado = df[~df["Nome do Cliente"].isin(clientes_excluir)]

# -----------------------------
# Limpeza e conversão de dados
# -----------------------------
df_filtrado["Valor Pago"] = (
    df_filtrado["Valor Pago"]
    .astype(str)
    .str.replace("R$", "", regex=False)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
)
df_filtrado["Valor Pago"] = pd.to_numeric(df_filtrado["Valor Pago"], errors="coerce")
df_filtrado = df_filtrado[df_filtrado["Valor Pago"].notna()]

# Converter a coluna Atendimento (ajuste o dayfirst se necessário)
df_filtrado["Atendimento"] = pd.to_datetime(
    df_filtrado["Atendimento"],
    dayfirst=False,
    errors="coerce"
)

# -----------------------------
# Métricas principais
# -----------------------------
faturamento_total = df_filtrado["Valor Pago"].sum()
ticket_medio = df_filtrado["Valor Pago"].mean()
pacientes = df_filtrado["Nome do Cliente"].nunique()
atendimentos = len(df_filtrado)

st.subheader("Métricas da clínica")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Faturamento Total", f"R$ {faturamento_total:,.2f}")
col2.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
col3.metric("Pacientes", pacientes)
col4.metric("Sessões", atendimentos)


# -----------------------------
# Novos pacientes por mês
# -----------------------------
# -----------------------------
# Novos pacientes por mês
# -----------------------------
primeiro_atendimento = (
    df_filtrado.sort_values("Atendimento")
                .groupby("Nome do Cliente")["Atendimento"]
                .first()
                .reset_index()
)
primeiro_atendimento["Mes"] = primeiro_atendimento["Atendimento"].dt.to_period("M")
novos_pacientes_mes = (
    primeiro_atendimento.groupby("Mes").size().reset_index(name="Novos Pacientes")
)
novos_pacientes_mes["Mes"] = novos_pacientes_mes["Mes"].astype(str)

# -----------------------------
# Faturamento mensal
# -----------------------------
df_filtrado["Mes"] = df_filtrado["Atendimento"].dt.strftime("%Y-%m")
faturamento_mes = df_filtrado.groupby("Mes")["Valor Pago"].sum().reset_index()

# -----------------------------
# Gráficos lado a lado
# -----------------------------
col1, col2 = st.columns(2)

col1.subheader("Novos pacientes por mês")
col1.bar_chart(novos_pacientes_mes.set_index("Mes"))

col2.subheader("Faturamento mensal")
col2.bar_chart(faturamento_mes.set_index("Mes"))

# -----------------------------
# Métricas do último mês lado a lado
# -----------------------------
if not novos_pacientes_mes.empty and not faturamento_mes.empty:
    col1, col2 = st.columns(2)
    col1.metric("Novos pacientes no último mês", novos_pacientes_mes.iloc[-1]["Novos Pacientes"])
    col2.metric("Faturamento no último mês", f"R$ {faturamento_mes.iloc[-1]['Valor Pago']:,.2f}")

# -----------------------------
# LTV por paciente e métricas lado a lado (KPIs em coluna)
# -----------------------------
ltv_paciente = (
    df_filtrado.groupby("Nome do Cliente")["Valor Pago"]
    .sum()
    .reset_index()
    .rename(columns={"Valor Pago": "LTV"})
)

st.subheader("LTV por paciente")

# Criar duas colunas: tabela e KPIs
col_table, col_kpis = st.columns([3, 1])

# Mostrar a tabela
col_table.dataframe(ltv_paciente)

# Calcular métricas
ltv_medio = ltv_paciente["LTV"].mean()
ltv_max = ltv_paciente["LTV"].max()
ltv_min = ltv_paciente["LTV"].min()

# Mostrar KPIs empilhados verticalmente
col_kpis.metric("LTV médio", f"R$ {ltv_medio:,.2f}")
col_kpis.metric("LTV máximo", f"R$ {ltv_max:,.2f}")
col_kpis.metric("LTV mínimo", f"R$ {ltv_min:,.2f}")

# -----------------------------
# Taxa de ocupação
# -----------------------------
capacidade_diaria = 6  # limite diário

periodo = st.selectbox(
    "Escolher período para a taxa de ocupação",
    options=["Diário", "Semanal", "Mensal"]
)

if periodo == "Diário":
    ocupacao = df_filtrado.groupby(df_filtrado["Atendimento"].dt.date)["Nome do Cliente"].count().reset_index()
    ocupacao.rename(columns={"Nome do Cliente": "Atendimentos"}, inplace=True)
    ocupacao["Taxa (%)"] = (ocupacao["Atendimentos"] / capacidade_diaria) * 100
    ocupacao = ocupacao.set_index("Atendimento")

elif periodo == "Semanal":
    ocupacao = df_filtrado.groupby(df_filtrado["Atendimento"].dt.to_period("W")).agg(
        Atendimentos=("Nome do Cliente", "count"),
        Dias_Ativos=("Atendimento", "nunique")
    ).reset_index()
    ocupacao["Taxa (%)"] = (ocupacao["Atendimentos"] / (ocupacao["Dias_Ativos"] * capacidade_diaria)) * 100
    ocupacao["Atendimento"] = ocupacao["Atendimento"].astype(str)
    ocupacao = ocupacao.set_index("Atendimento")

elif periodo == "Mensal":
    ocupacao = df_filtrado.groupby(df_filtrado["Atendimento"].dt.to_period("M")).agg(
        Atendimentos=("Nome do Cliente", "count"),
        Dias_Ativos=("Atendimento", "nunique")
    ).reset_index()
    ocupacao["Taxa (%)"] = (ocupacao["Atendimentos"] / (ocupacao["Dias_Ativos"] * capacidade_diaria)) * 100
    ocupacao["Atendimento"] = ocupacao["Atendimento"].astype(str)
    ocupacao = ocupacao.set_index("Atendimento")

st.subheader(f"Taxa de ocupação ({periodo})")
st.line_chart(ocupacao["Taxa (%)"])

# # -----------------------------
# # Mostrar dados brutos
# # -----------------------------
# st.subheader("Dados da planilha")
# st.dataframe(df_filtrado)
