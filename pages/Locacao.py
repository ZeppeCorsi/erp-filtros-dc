import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from streamlit_gsheets import GSheetsConnection
import gspread # Certifique-se de que está no requirements.txt

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
    st.subheader("📑 Gestão de Locação - Filtros DC")
    
    df_clientes = carregar_dados("Clientes")
    df_produtos = carregar_dados("Produtos")
    
    with st.form("nova_locacao", clear_on_submit=True):
        st.markdown("### Registrar Contrato e Provisionar 12 Meses")
        col1, col2 = st.columns(2)
        
        with col1:
            data_ini = st.date_input("Início da Locação", value=date.today())
            lista_cli = sorted(df_clientes["NOME REDUZIDO"].dropna().unique().tolist()) if not df_clientes.empty else ["Vazio"]
            cliente = st.selectbox("Cliente", options=lista_cli)
            
            # Ajustado para usar a coluna 'NOME' conforme sua imagem
            lista_prod = sorted(df_produtos["NOME"].dropna().unique().tolist()) if not df_produtos.empty else ["Vazio"]
            produto = st.selectbox("Equipamento (Filtro)", options=lista_prod)
            
        with col2:
            valor_mensal = st.number_input("Valor Mensal (R$)", min_value=0.0, format="%.2f")
            custo_total = 0.0
            if not df_produtos.empty and produto != "Vazio":
                filtro = df_produtos.loc[df_produtos["NOME"] == produto, "CUSTO TOTAL"]
                if not filtro.empty:
                    custo_total = float(filtro.values[0])
            st.info(f"Custo de Aquisição: R$ {custo_total:,.2f}")

        if st.form_submit_button("Gerar Locação e Lançamentos"):
            try:
                # --- CORREÇÃO DO ACESSO AO GSPREAD ---
                # Acessamos as credenciais através da conexão do Streamlit
                credentials = conn._instance._credentials
                client = gspread.authorize(credentials)
                
                # Abre a planilha pelo ID ou URL definida nos secrets
                spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                ss = client.open_by_url(spreadsheet_url)

                # 1. ABA LOCACAO
                ws_loc = ss.worksheet("Locacao")
                ws_loc.append_row([data_ini.strftime("%d/%m/%Y"), cliente, produto, valor_mensal, custo_total])

                # 2. GERAÇÃO DAS 12 PARCELAS
                ws_caixa = ss.worksheet("Fluxo de Caixa")
                ws_vendas = ss.worksheet("Vendas")
                
                caixa_rows = []
                vendas_rows = []

                for i in range(1, 13):
                    vencimento = (data_ini + relativedelta(months=i-1)).replace(day=5)
                    dt_str = vencimento.strftime("%d/%m/%Y")
                    
                    # Fluxo de Caixa: DATA; TIPO; DESCRICAO; VALOR; PARCELA; STATUS; CLIENTE; NF
                    caixa_rows.append([dt_str, "ENTRADA", f"LOCACAO - {produto}", valor_mensal, f"{i}/12", "PREVISTO", cliente, "LOC"])

                    # Vendas (14 colunas): NF; DATA; CLIENTE; PRODUTO; CFOPS; TOTAL; COMPRAS; FORMA DE PAGAMENTO; QTD; VALOR UNIT; VENDEDOR; OBS; CUSTO; MARGEM
                    vendas_rows.append(["LOC", dt_str, cliente, produto, "LOC", valor_mensal, 0, "BOLETO/LOC", 1, valor_mensal, "SISTEMA", f"Parc {i}/12", 0, valor_mensal])
                
                ws_caixa.append_rows(caixa_rows)
                ws_vendas.append_rows(vendas_rows)

                st.success(f"✅ Locação ativada! Lançamentos realizados no Fluxo e Vendas.")
                st.balloons()

            except Exception as e:
                st.error(f"Erro técnico ao gravar: {e}")
                st.info("Dica: Verifique se a biblioteca 'gspread' está instalada.")

if __name__ == "__main__":
    aba_gestao_locacao()