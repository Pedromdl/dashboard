import pandas as pd
import streamlit as st
from data_loader import carregar_dados
from financeiro import mostrar_financeiro
from pacientes import mostrar_pacientes, novos_pacientes_por_mes
from marketing import mostrar_marketing, custo_por_mes

st.title("Dashboard da Clínica")

df_todos_anos = carregar_dados()

# filtro de ano
anos_disponiveis = sorted(df_todos_anos["Ano"].dropna().unique())

ano_selecionado = st.selectbox(
    "Escolher ano para análise",
    options=["Todos"] + [str(int(a)) for a in anos_disponiveis]
)

if ano_selecionado != "Todos":
    df_filtrado = df_todos_anos[
        df_todos_anos["Ano"] == int(ano_selecionado)
    ]
else:
    df_filtrado = df_todos_anos.copy()

custo = custo_por_mes()
novos = novos_pacientes_por_mes(df_todos_anos, ano_selecionado)

# excluir pacientes
clientes_excluir = st.multiselect(
    "Selecionar clientes para excluir",
    options=df_filtrado["Nome do Cliente"].unique()
)

df_filtrado = df_filtrado[
    ~df_filtrado["Nome do Cliente"].isin(clientes_excluir)
]

# financeiro
faturamento_mes = mostrar_financeiro(df_filtrado)
# juntar pelo mês
df_cac = pd.merge(custo, novos, on="Mes", how="inner")

df_cac["CAC"] = df_cac["Custo"] / df_cac["Novos Pacientes"]

st.metric("CAC Médio", f"R$ {df_cac['CAC'].mean():,.2f}")
st.header("💰 CAC - Custo de Aquisição de Cliente")
st.line_chart(
    df_cac.set_index("Mes")["CAC"],
    height=200
)

# pacientes
mostrar_pacientes(
    df_filtrado,
    df_todos_anos,
    ano_selecionado
)

mostrar_marketing()