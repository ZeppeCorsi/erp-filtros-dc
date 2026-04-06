import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
# Importação correta para evitar o NameError
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA CONEXÃO
# ttl=0 garante que ele busque dados novos da planilha sempre
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def carregar_dados(aba):
    try:
        df = conn.read(worksheet=aba)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar aba {aba}: {e}")
        return pd.DataFrame()

def aba_gestao_locacao():
    st.subheader("📑 Gestão de Locação e Automação ERP")
    
    # Carrega dados para os seletores
    df_clientes = carregar_dados("Clientes")
    df_produtos = carregar_dados("Produtos")
    
    with st.form("nova_locacao", clear_on_submit=True):
        st.markdown("### Cadastrar e Provisionar 12 Meses")
        col1, col2 = st.columns(2)
        
        with col1:
            data_ini = st.date_input("Início da Locação", value=date.today())
            lista_cli = sorted(df_clientes["NOME REDUZIDO"].dropna().unique().tolist()) if not df_clientes.empty else ["Vazio"]
            cliente = st.selectbox("Cliente", options=lista_cli)
            
            lista_prod = sorted(df_produtos["NOME"].dropna().unique().tolist()) if not df_produtos.empty else ["Vazio"]
            produto = st.selectbox("Equipamento", options=lista_prod)
            
        with col2:
            valor_mensal = st.number_input("Valor Mensal (R$)", min_value=0.0, format="%.2f")
            
            custo_total = 0.0
            if not df_produtos.empty and produto != "Vazio":
                # Busca o custo na coluna CUSTO TOTAL
                filtro_prod = df_produtos.loc[df_produtos["NOME"] == produto, "CUSTO TOTAL"]
                if not filtro_prod.empty:
                    custo_total = float(filtro_prod.values[0])
            
            st.info(f"Custo de Aquisição: R$ {custo_total:,.2f}")

        # O botão que faltava e que agora processa a gravação
        submit = st.form_submit_button("Confirmar e Gerar 12 Meses")

        if submit:
            try:
                # Usando o método nativo do streamlit-gsheets para atualizar/adicionar linhas
                # Se sua versão for recente, usamos o conn.create ou conn.update
                
                # 1. Dados para a aba LOCACAO
                df_nova_loc = pd.DataFrame([{
                    "DATA_INICIO": data_ini.strftime("%d/%m/%Y"),
                    "CLIENTE": cliente,
                    "EQUIPAMENTO": produto,
                    "VALOR_MENSAL": valor_mensal,
                    "CUSTO_ORIGINAL": custo_total
                }])

                # 2. Gerar lista para Fluxo e Vendas
                lista_caixa = []
                lista_vendas = []

                for i in range(1, 13):
                    vencimento = (data_ini + relativedelta(months=i-1)).replace(day=5)
                    dt_str = vencimento.strftime("%d/%m/%Y")
                    
                    # Fluxo de Caixa
                    lista_caixa.append({
                        "DATA": dt_str, "TIPO": "ENTRADA", "DESCRICAO": f"LOCACAO - {produto}",
                        "VALOR": valor_mensal, "PARCELA": f"{i}/12", "STATUS": "PREVISTO",
                        "CLIENTE": cliente, "NF": "LOC"
                    })
                    
                    # Vendas
                    lista_vendas.append({
                        "NF": "LOC", "DATA": dt_str, "CLIENTE": cliente, "PRODUTO": produto,
                        "CFOPS": "LOC", "TOTAL": valor_mensal, "COMPRAS": 0,
                        "FORMA DE PAGAMENTO": "MENSALIDADE", "QTD": 1, "VALOR UNIT": valor_mensal,
                        "VENDEDOR": "SISTEMA", "OBS": f"Parc {i}/12", "CUSTO": 0, "MARGEM": valor_mensal
                    })

                # Gravando via Streamlit GSheets (método mais estável)
                # Nota: append_row pode não existir, então concatenamos e sobrescrevemos ou usamos create
                
                # Para garantir a gravação, vamos usar o client direto se disponível
                ws_client = conn._instance.client
                ss = ws_client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
                
                ss.worksheet("Locacao").append_row(df_nova_loc.values.tolist()[0])
                ss.worksheet("Fluxo de Caixa").append_rows([list(d.values()) for d in lista_caixa])
                ss.worksheet("Vendas").append_rows([list(d.values()) for d in lista_vendas])

                st.success(f"✅ Locação e 12 parcelas de R$ {valor_mensal} geradas com sucesso!")
                st.balloons()
                
            except Exception as e:
                st.error(f"Erro ao gravar dados: {e}. Verifique se as abas existem com os nomes exatos.")

if __name__ == "__main__":
    aba_gestao_locacao()