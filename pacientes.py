import streamlit as st
import pandas as pd


def novos_pacientes_por_mes(df_todos_anos, ano_selecionado):

    primeiro_atendimento = (
        df_todos_anos.sort_values("Atendimento")
        .groupby("Nome do Cliente")["Atendimento"]
        .first()
        .reset_index()
    )

    primeiro_atendimento["Atendimento"] = pd.to_datetime(
        primeiro_atendimento["Atendimento"],
        errors="coerce"
    )

    primeiro_atendimento["Ano"] = primeiro_atendimento["Atendimento"].dt.year

    primeiro_atendimento["Mes"] = (
        primeiro_atendimento["Atendimento"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    if ano_selecionado != "Todos":
        primeiro_atendimento = primeiro_atendimento[
            primeiro_atendimento["Ano"] == int(ano_selecionado)
        ]

    novos = (
        primeiro_atendimento.groupby("Mes")
        .size()
        .reset_index(name="Novos Pacientes")
        .sort_values("Mes")
    )

    return novos


def mostrar_pacientes(df_filtrado, df_todos_anos, ano_selecionado):

    # Garantir datetime
    df_filtrado["Atendimento"] = pd.to_datetime(
        df_filtrado["Atendimento"],
        errors="coerce"
    )

    # =============================
    # NOVOS PACIENTES
    # =============================
    novos_pacientes_mes = novos_pacientes_por_mes(
        df_todos_anos,
        ano_selecionado
    )

    # =============================
    # LTV
    # =============================
    ltv_paciente = (
        df_filtrado.groupby("Nome do Cliente")["Valor Pago"]
        .sum()
        .reset_index()
        .rename(columns={"Valor Pago": "LTV"})
    )

    # =============================
    # KPIs
    # =============================
    total_pacientes = novos_pacientes_mes["Novos Pacientes"].sum()
    total_sessoes = len(df_filtrado)

    sessoes_por_paciente = (
        total_sessoes / total_pacientes
        if total_pacientes > 0 else 0
    )

    st.subheader("🧑 Performance de Pacientes")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total de pacientes", total_pacientes)
    col2.metric("Sessões realizadas", total_sessoes)
    col3.metric("Sessões por paciente", f"{sessoes_por_paciente:.1f}")
    col4.metric("LTV médio", f"R$ {ltv_paciente['LTV'].mean():,.2f}")

    st.divider()

    # =============================
    # GRÁFICOS
    # =============================
    col_graf1, col_graf2 = st.columns(2)

    # ----- Novos Pacientes -----
    with col_graf1:
        st.subheader("Novos pacientes por mês")
        st.bar_chart(
            novos_pacientes_mes.set_index("Mes"),
            use_container_width=True
        )

    # ----- Taxa de Ocupação -----
    with col_graf2:

        header_col1, header_col2 = st.columns([3, 1])

        with header_col1:
            st.subheader("Taxa de ocupação")

        with header_col2:
            periodo = st.selectbox(
                "Período",
                ["Diário", "Semanal", "Mensal"],
                label_visibility="collapsed",
                key="periodo_ocupacao"
            )

        capacidade_diaria = 6

        if periodo == "Diário":
            ocupacao = (
                df_filtrado.groupby(
                    df_filtrado["Atendimento"].dt.date
                )["Nome do Cliente"]
                .count()
                .reset_index(name="Atendimentos")
            )

            ocupacao["Taxa (%)"] = (
                ocupacao["Atendimentos"] / capacidade_diaria
            ) * 100

            ocupacao = ocupacao.set_index("Atendimento")

        elif periodo == "Semanal":
            ocupacao = (
                df_filtrado.groupby(
                    df_filtrado["Atendimento"].dt.to_period("W")
                )
                .agg(
                    Atendimentos=("Nome do Cliente", "count"),
                    Dias_Ativos=("Atendimento", "nunique")
                )
                .reset_index()
            )

            ocupacao["Taxa (%)"] = (
                ocupacao["Atendimentos"] /
                (ocupacao["Dias_Ativos"] * capacidade_diaria)
            ) * 100

            ocupacao["Atendimento"] = ocupacao["Atendimento"].astype(str)
            ocupacao = ocupacao.set_index("Atendimento")

        else:
            ocupacao = (
                df_filtrado.groupby(
                    df_filtrado["Atendimento"].dt.to_period("M")
                )
                .agg(
                    Atendimentos=("Nome do Cliente", "count"),
                    Dias_Ativos=("Atendimento", "nunique")
                )
                .reset_index()
            )

            ocupacao["Taxa (%)"] = (
                ocupacao["Atendimentos"] /
                (ocupacao["Dias_Ativos"] * capacidade_diaria)
            ) * 100

            ocupacao["Atendimento"] = ocupacao["Atendimento"].astype(str)
            ocupacao = ocupacao.set_index("Atendimento")

        ocupacao = ocupacao.sort_index()

        st.line_chart(
            ocupacao["Taxa (%)"],
            use_container_width=True,
            height=350
        )

    # =============================
    # LTV POR PACIENTE
    # =============================
    st.subheader("LTV por paciente")

    col_table, col_kpis = st.columns([2, 1])

    col_table.dataframe(ltv_paciente)

    col_kpis.metric("LTV máximo", f"R$ {ltv_paciente['LTV'].max():,.2f}")
    col_kpis.metric("LTV mínimo", f"R$ {ltv_paciente['LTV'].min():,.2f}")