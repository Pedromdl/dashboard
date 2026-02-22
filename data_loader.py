import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def carregar_dados():

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )
    client = gspread.authorize(creds)

    abas_anos = ["2024", "2025", "2026"]
    dfs = []

    planilhas_urls = [
        "https://docs.google.com/spreadsheets/d/1h5gdng8DNF8RVfknGnvRj-x2Vbx-ZeCrGhD_GKNuPFI",
        "https://docs.google.com/spreadsheets/d/1k00rq893Sss2F2AXQn_K7_nixmVASte6RmphFDbwMEg"
    ]

    for url in planilhas_urls:
        planilha = client.open_by_url(url)
        abas_existentes = [ws.title for ws in planilha.worksheets()]

        for aba in abas_anos:
            if aba in abas_existentes:
                sheet_aba = planilha.worksheet(aba)
                data_aba = sheet_aba.get_all_values()

                columns = [
                    c if c.strip() != "" else f"Coluna_{i}"
                    for i, c in enumerate(data_aba[0])
                ]

                df_aba = pd.DataFrame(data_aba[1:], columns=columns)

                df_aba["Valor Pago"] = (
                    df_aba["Valor Pago"]
                    .astype(str)
                    .str.replace("R$", "", regex=False)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                )

                df_aba["Valor Pago"] = pd.to_numeric(
                    df_aba["Valor Pago"], errors="coerce"
                )

                df_aba["Atendimento"] = pd.to_datetime(
                    df_aba["Atendimento"],
                    dayfirst=False,
                    errors="coerce"
                )

                dfs.append(df_aba)

    df = pd.concat(dfs, ignore_index=True)
    df["Ano"] = df["Atendimento"].dt.year

    return df