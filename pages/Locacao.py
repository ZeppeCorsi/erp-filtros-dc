import streamlit as st
import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from streamlit_gsheets import GSheetsConnection

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
            # 1. SALVAR NA ABA 'LOCACAO' (Registro Mestre)
            dados_loc = [[
                data_ini.strftime("%d/%m/%Y"), 
                cliente, 
                produto, 
                valor_mensal, 
                custo_total
            ]]
            conn.append_row(dados_loc, worksheet="Locacao")

            # 2. GERAR 12 PARCELAS PARA 'FLUXO DE CAIXA' E 'VENDAS'
            for i in range(1, 13):
                # Calcula a data de vencimento (todo dia 05 do mês subsequente)
                vencimento = (data_ini + relativedelta(months=i-1)).replace(day=5)
                data_str = vencimento.strftime("%d/%m/%Y")
                
                # --- Lançamento Fluxo de Caixa ---
                # Colunas: DATA; TIPO; DESCRICAO; VALOR; PARCELA; STATUS; CLIENTE; NF
                dados_caixa = [[
                    data_str, 
                    "ENTRADA", 
                    f"LOCACAO MENSAL - {produto}", 
                    valor_mensal, 
                    f"{i}/12", 
                    "PREVISTO", 
                    cliente, 
                    "LOC"
                ]]
                conn.append_row(dados_caixa, worksheet="Fluxo de Caixa")

                # --- Lançamento Vendas ---
                # Colunas: NF; DATA; CLIENTE; PRODUTO; CFOPS; TOTAL; COMPRAS; FORMA DE PAGAMENTO; QTD; VALOR UNIT; VENDEDOR; OBS; CUSTO; MARGEM
                dados_vendas = [[
                    "LOC", 
                    data_str, 
                    cliente, 
                    produto, 
                    "LOC", 
                    valor_mensal, 
                    0, 
                    "MENSALIDADE", 
                    1, 
                    valor_mensal, 
                    "SISTEMA", 
                    f"Parcela {i}/12", 
                    0, 
                    valor_mensal
                ]]
                conn.append_row(dados_vendas, worksheet="Vendas")
            
            st.success(f"✅ Sucesso! 12 parcelas de R$ {valor_mensal} registradas para {cliente}.")

if __name__ == "__main__":
    aba_gestao_locacao()