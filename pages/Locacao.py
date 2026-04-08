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
    st.subheader("📑 Gestão de Locação - Filtros DC")
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. INICIALIZAÇÃO DE VARIÁVEIS (Evita erros de "not defined")
    df_clientes = conn.read(worksheet="Clientes", ttl=0)
    df_produtos = conn.read(worksheet="Produtos", ttl=0)
    valor_mensal = 0.0
    custo_total = 0.0
    
    with st.form("nova_locacao", clear_on_submit=True):
        st.markdown("### Registrar Contrato e Gerar Parcelas Futuras")
        col1, col2 = st.columns(2)
        
        with col1:
            data_ini = st.date_input("Data Original do Contrato", value=date.today())
            lista_cli = sorted(df_clientes["NOME REDUZIDO"].dropna().unique().tolist()) if df_clientes is not None else []
            cliente = st.selectbox("Cliente", options=lista_cli)
            
            lista_prod = sorted(df_produtos["NOME"].dropna().unique().tolist()) if df_produtos is not None else []
            produto = st.selectbox("Equipamento (Filtro)", options=lista_prod)
            
        with col2:
            valor_mensal = st.number_input("Valor Mensal (R$)", min_value=0.0, format="%.2f")
            # PERGUNTA QUANTAS PARCELAS LANÇAR A PARTIR DE HOJE
            qtd_para_lancar = st.number_input("Quantas parcelas lançar (a partir de hoje)?", min_value=1, value=12)
            
            if df_produtos is not None and produto:
                busca_custo = df_produtos.loc[df_produtos["NOME"] == produto, "CUSTO TOTAL"]
                custo_total = float(busca_custo.values[0]) if not busca_custo.empty else 0.0

        if st.form_submit_button("Gerar Locação e Lançamentos"):
            try:
                # Lendo dados atuais
                df_loc_atual = conn.read(worksheet="Locacao", ttl=0).dropna(how='all')
                df_fluxo_antigo = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
                df_vendas_antigo = conn.read(worksheet="Vendas", ttl=0).dropna(how='all')

                # A) Grava na aba Locacao (Histórico com total de parcelas)
                nova_linha_loc = pd.DataFrame([{
                    "DATA_INICIO": data_ini.strftime("%d/%m/%Y"),
                    "CLIENTE": cliente,
                    "EQUIPAMENTO": produto,
                    "VALOR_MENSAL": valor_mensal,
                    "CUSTO_ORIGINAL": custo_total,
                    "TOTAL_PARCELAS": qtd_para_lancar # Corrigindo o "None"
                }])
                conn.update(worksheet="Locacao", data=pd.concat([df_loc_atual, nova_linha_loc], ignore_index=True))

                # B) Gera parcelas a partir de HOJE
                novas_vendas = []
                novos_fluxos = []
                hoje = date.today()

                for i in range(1, int(qtd_para_lancar) + 1):
                    # Vencimento sempre no dia 5 dos meses subsequentes a hoje
                    vencimento = (hoje + relativedelta(months=i-1)).replace(day=5)
                    dt_str = vencimento.strftime("%d/%m/%Y")
                    
                    # Fluxo como PENDENTE
                    novos_fluxos.append({
                        "DATA": dt_str, "TIPO": "ENTRADA", "DESCRICAO": f"LOCACAO - {produto}",
                        "VALOR": valor_mensal, "PARCELA": f"{i}/{qtd_para_lancar}", 
                        "STATUS": "PENDENTE", "CLIENTE": cliente, "NF": "LOC"
                    })

                    # Vendas
                    novas_vendas.append({
                        "NF": "LOC", "DATA": dt_str, "CLIENTE": cliente, "PRODUTO": produto,
                        "CFOPS": "LOC", "TOTAL": valor_mensal, "COMPRAS": 0,
                        "FORMA DE PAGAMENTO": "BOLETO/LOC", "QTD": 1, "VALOR UNIT": valor_mensal,
                        "VENDEDOR": "SISTEMA", "OBS": f"Parc {i}/{qtd_para_lancar}", 
                        "CUSTO": 0, "MARGEM": valor_mensal
                    })
                
                # C) Atualização das abas
                df_f_final = pd.concat([df_fluxo_antigo, pd.DataFrame(novos_fluxos)], ignore_index=True)
                conn.update(worksheet="Fluxo de Caixa", data=df_f_final.iloc[:, :8])
                
                df_v_final = pd.concat([df_vendas_antigo, pd.DataFrame(novas_vendas)], ignore_index=True)
                conn.update(worksheet="Vendas", data=df_v_final.iloc[:, :14])

                st.success(f"✅ Sucesso! Lançadas {qtd_para_lancar} parcelas (Status: PENDENTE) iniciando em {hoje.strftime('%m/%Y')}.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro na gravação: {e}")

    # Exibição da tabela de contratos
    st.markdown("---")
    df_visualizar = conn.read(worksheet="Locacao", ttl=0)
    if df_visualizar is not None:
        st.write("### 📋 Contratos Registrados")
        st.dataframe(df_visualizar, use_container_width=True, hide_index=True)