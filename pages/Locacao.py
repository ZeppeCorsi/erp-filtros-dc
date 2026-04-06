import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def carregar_dados(aba):
    try:
        df = conn.read(worksheet=aba)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def aba_gestao_locacao():
    st.subheader("📑 Gestão de Locação e Automação ERP")
    
    df_clientes = carregar_dados("Clientes")
    df_produtos = carregar_dados("Produtos")
    
    with st.form("nova_locacao", clear_on_submit=True):
        st.markdown("### Cadastrar e Provisionar 12 Meses")
        col1, col2 = st.columns(2)
        
        with col1:
            data_ini = st.date_input("Início da Locação", value=date.today())
            cliente = st.selectbox("Cliente", options=df_clientes["NOME REDUZIDO"].unique() if not df_clientes.empty else ["Vazio"])
            produto = st.selectbox("Equipamento", options=df_produtos["NOME"].unique() if not df_produtos.empty else ["Vazio"])
            
        with col2:
            valor_mensal = st.number_input("Valor Mensal (R$)", min_value=0.0, format="%.2f")
            custo_total = 0.0
            if not df_produtos.empty and produto != "Vazio":
                custo_total = df_produtos.loc[df_produtos["NOME"] == produto, "CUSTO TOTAL"].values[0]
            st.info(f"Custo de Aquisição: R$ {custo_total:,.2f}")

        if st.form_submit_button("Confirmar e Gerar Lançamentos"):
            try:
                # Acessando o gspread interno para usar append_row
                # Nota: Em algumas versões do Streamlit, usa-se conn._instance.client
                client = conn.session
                spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                sh = client.open_by_url(spreadsheet_url)

                # --- 1. GRAVAR NA ABA 'LOCACAO' ---
                ws_loc = sh.worksheet("Locacao")
                ws_loc.append_row([data_ini.strftime("%d/%m/%Y"), cliente, produto, valor_mensal, custo_total])

                # --- 2. GERAR 12 PARCELAS ---
                ws_caixa = sh.worksheet("Fluxo de Caixa")
                ws_vendas = sh.worksheet("Vendas")

                for i in range(1, 13):
                    # Data de vencimento: Todo dia 05 do mês subsequente
                    vencimento = (data_ini + relativedelta(months=i-1)).replace(day=5)
                    data_str = vencimento.strftime("%d/%m/%Y")
                    
                    # Fluxo de Caixa: DATA; TIPO; DESCRICAO; VALOR; PARCELA; STATUS; CLIENTE; NF
                    ws_caixa.append_row([data_str, "ENTRADA", f"LOCACAO - {produto}", valor_mensal, f"{i}/12", "PREVISTO", cliente, "LOC"])

                    # Vendas: NF; DATA; CLIENTE; PRODUTO; CFOPS; TOTAL; COMPRAS; FORMA DE PAGAMENTO; QTD; VALOR UNIT; VENDEDOR; OBS; CUSTO; MARGEM
                    ws_vendas.append_row(["LOC", data_str, cliente, produto, "LOC", valor_mensal, 0, "MENSALIDADE", 1, valor_mensal, "SISTEMA", f"Parc {i}/12", 0, valor_mensal])
                
                st.success(f"✅ Sucesso! 12 parcelas registradas para {cliente}.")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao gravar na planilha: {e}")

if __name__ == "__main__":
    aba_gestao_locacao()