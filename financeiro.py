import streamlit as st

def mostrar_financeiro(df):

    faturamento_total = df["Valor Pago"].sum()
    ticket_medio = df["Valor Pago"].mean()

    st.subheader("Financeiro")

    col1, col2 = st.columns(2)

    col1.metric("Faturamento Total", f"R$ {faturamento_total:,.2f}")
    col2.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
    