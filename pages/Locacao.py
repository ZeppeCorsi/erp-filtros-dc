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
        # Remove colunas e linhas totalmente vazias
        df = df.dropna(how='all').dropna(axis=1, how='all')
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

        submit = st.form_submit_button("Gerar Locação e Lançamentos")

        if submit:
            try:
                # --- SOLUÇÃO PARA NÃO SOBRESCREVER ---
                
                # 1. ABA LOCACAO (Garante que as colunas batam)
                df_loc_antigo = conn.read(worksheet="Locacao").dropna(how='all')
                nova_loc = pd.DataFrame([{
                    "DATA_INICIO": data_ini.strftime("%d/%m/%Y"),
                    "CLIENTE": cliente,
                    "EQUIPAMENTO": produto,
                    "VALOR_MENSAL": valor_mensal,
                    "CUSTO_ORIGINAL": custo_total
                }])
                df_loc_final = pd.concat([df_loc_antigo, nova_loc], ignore_index=True)
                conn.update(worksheet="Locacao", data=df_loc_final)

                # 2. ABA FLUXO DE CAIXA E VENDAS
                df_fluxo_antigo = conn.read(worksheet="Fluxo de Caixa").dropna(how='all')
                df_vendas_antigo = conn.read(worksheet="Vendas").dropna(how='all')
                
                novas_vendas = []
                novos_fluxos = []

                for i in range(1, 13):
                    vencimento = (data_ini + relativedelta(months=i-1)).replace(day=5)
                    dt_str = vencimento.strftime("%d/%m/%Y")
                    
                    novos_fluxos.append({
                        "DATA": dt_str, "TIPO": "ENTRADA", "DESCRICAO": f"LOCACAO - {produto}",
                        "VALOR": valor_mensal, "PARCELA": f"{i}/12", "STATUS": "PREVISTO", 
                        "CLIENTE": cliente, "NF": "LOC"
                    })

                    # Criamos exatamente as 14 colunas da imagem
                    novas_vendas.append({
                        "NF": "LOC", "DATA": dt_str, "CLIENTE": cliente, "PRODUTO": produto,
                        "CFOPS": "LOC", "TOTAL": valor_mensal, "COMPRAS": 0,
                        "FORMA DE PAGAMENTO": "BOLETO/LOC", "QTD": 1, "VALOR UNIT": valor_mensal,
                        "VENDEDOR": "SISTEMA", "OBS": f"Parc {i}/12", "CUSTO": 0, "MARGEM": valor_mensal
                    })
                
                # Garante que não haja colunas extras (index=False)
                df_fluxo_final = pd.concat([df_fluxo_antigo, pd.DataFrame(novos_fluxos)], ignore_index=True)
                df_vendas_final = pd.concat([df_vendas_antigo, pd.DataFrame(novas_vendas)], ignore_index=True)
                
                # REPARO CRÍTICO: Força o número de colunas a ser igual ao original
                df_vendas_final = df_vendas_final.iloc[:, :14]
                df_fluxo_final = df_fluxo_final.iloc[:, :8]

                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo_final)
                conn.update(worksheet="Vendas", data=df_vendas_final)

                st.success("✅ Tudo gravado corretamente no final das listas!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

    # --- TABELA DE CONTROLE (IDENTADA PARA APARECER SEMPRE) ---
    st.markdown("---")
    st.markdown("### 📅 Controle de Contratos (Vencimento da 12ª Parcela)")
    
    df_controle = carregar_dados("Locacao")
    
    if not df_controle.empty:
        try:
            # Converte data ignorando erros
            df_controle['DATA_INICIO_DT'] = pd.to_datetime(df_controle['DATA_INICIO'], dayfirst=True, errors='coerce')
            df_controle = df_controle.dropna(subset=['DATA_INICIO_DT'])
            
            # Cálculo da 12ª parcela
            df_controle['VENC_12'] = df_controle['DATA_INICIO_DT'].apply(lambda x: (x + relativedelta(months=11)).replace(day=5))
            df_controle['DIAS'] = (df_controle['VENC_12'] - pd.Timestamp(date.today())).dt.days
            
            # Formatação
            df_view = df_controle.copy()
            df_view['12ª PARCELA'] = df_view['VENC_12'].dt.strftime('%d/%m/%Y')
            df_view = df_view.rename(columns={'EQUIPAMENTO': 'PRODUTO', 'VALOR_MENSAL': 'VALOR'})

            st.dataframe(
                df_view[['CLIENTE', 'PRODUTO', 'VALOR', '12ª PARCELA', 'DIAS']]
                .style.applymap(lambda x: 'color: red' if isinstance(x, int) and x <= 30 else 'color: black', subset=['DIAS'])
            )
        except Exception as e:
            st.write("Aguardando novos dados formatados...")
    else:
        st.info("Nenhuma locação ativa na aba 'Locacao'.")

if __name__ == "__main__":
    aba_gestao_locacao()