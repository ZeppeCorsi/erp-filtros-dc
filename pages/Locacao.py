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
    
    df_clientes = carregar_dados("Clientes")
    df_produtos = carregar_dados("Produtos")
    
    with st.form("nova_locacao", clear_on_submit=True):
        st.markdown("### Registrar Contrato Personalizado")
        col1, col2 = st.columns(2)
        
        with col1:
            data_ini = st.date_input("Início da Locação", value=date.today())
            lista_cli = sorted(df_clientes["NOME REDUZIDO"].dropna().unique().tolist()) if not df_clientes.empty else ["Vazio"]
            cliente = st.selectbox("Cliente", options=lista_cli)
            
            lista_prod = sorted(df_produtos["NOME"].dropna().unique().tolist()) if not df_produtos.empty else ["Vazio"]
            produto = st.selectbox("Equipamento (Filtro)", options=lista_prod)
            
        with col2:
            valor_mensal = st.number_input("Valor Mensal (R$)", min_value=0.0, format="%.2f")
            # --- NOVA PERGUNTA: QUANTIDADE DE PARCELAS ---
            qtd_parcelas = st.number_input("Quantidade de Parcelas (Ciclo)", min_value=1, max_value=48, value=12)
            
            custo_total = 0.0
            if not df_produtos.empty and produto != "Vazio":
                filtro = df_produtos.loc[df_produtos["NOME"] == produto, "CUSTO TOTAL"]
                if not filtro.empty:
                    custo_total = float(filtro.values[0])
            st.info(f"Custo de Aquisição: R$ {custo_total:,.2f}")

        if st.form_submit_button("Gerar Locação e Lançamentos"):
            try:
                # 1. Gravação na aba Locacao (Histórico do Contrato)
                df_loc_atual = conn.read(worksheet="Locacao", ttl=0).dropna(how='all')
                nova_linha_loc = pd.DataFrame([{
                    "DATA_INICIO": data_ini.strftime("%d/%m/%Y"),
                    "CLIENTE": cliente,
                    "EQUIPAMENTO": produto,
                    "VALOR_MENSAL": valor_mensal,
                    "CUSTO_ORIGINAL": custo_total,
                    "TOTAL_PARCELAS": qtd_parcelas # Guardamos o ciclo escolhido
                }])
                conn.update(worksheet="Locacao", data=pd.concat([df_loc_atual, nova_linha_loc], ignore_index=True))

                # 2. Preparar as parcelas para Fluxo e Vendas
                df_fluxo_atual = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
                df_vendas_atual = conn.read(worksheet="Vendas", ttl=0).dropna(how='all')
                
                novas_vendas = []
                novos_fluxos = []

                # Data de corte para não retroagir (Abril/2026 conforme conversamos)
                data_corte = date(2026, 4, 1)

                for i in range(1, int(qtd_parcelas) + 1):
                    vencimento = (data_ini + relativedelta(months=i-1)).replace(day=5)
                    
                    # Só lança se o vencimento for a partir de Abril/2026
                    if vencimento >= data_corte:
                        dt_str = vencimento.strftime("%d/%m/%Y")
                        
                        # Dados Fluxo - Alterado para PENDENTE
                        novos_fluxos.append({
                            "DATA": dt_str, "TIPO": "ENTRADA", "DESCRICAO": f"LOCACAO - {produto}",
                            "VALOR": valor_mensal, "PARCELA": f"{i}/{qtd_parcelas}", 
                            "STATUS": "PENDENTE", # <--- ALTERADO AQUI
                            "CLIENTE": cliente, "NF": "LOC"
                        })

                        # Dados Vendas
                        novas_vendas.append({
                            "NF": "LOC", "DATA": dt_str, "CLIENTE": cliente, "PRODUTO": produto,
                            "CFOPS": "LOC", "TOTAL": valor_mensal, "COMPRAS": 0,
                            "FORMA DE PAGAMENTO": "BOLETO/LOC", "QTD": 1, "VALOR UNIT": valor_mensal,
                            "VENDEDOR": "SISTEMA", "OBS": f"Parc {i}/{qtd_parcelas}", "CUSTO": 0, "MARGEM": valor_mensal
                        })
                
                # Atualização final
                if novos_fluxos:
                    df_fluxo_final = pd.concat([df_fluxo_atual, pd.DataFrame(novos_fluxos)], ignore_index=True).iloc[:, :8]
                    conn.update(worksheet="Fluxo de Caixa", data=df_fluxo_final)
                
                if novas_vendas:
                    df_vendas_final = pd.concat([df_vendas_atual, pd.DataFrame(novas_vendas)], ignore_index=True).iloc[:, :14]
                    conn.update(worksheet="Vendas", data=df_vendas_final)

                st.success(f"✅ Locação de {qtd_parcelas} meses gerada! Lançamentos a partir de Abril/2026 definidos como PENDENTE.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

    # --- LISTA DE CONTROLE (VISUALIZAÇÃO) ---
    st.markdown("---")
    df_controle = carregar_dados("Locacao")
    if not df_controle.empty:
        # Lógica de exibição similar à anterior, mas usando a coluna dinâmica de parcelas
        st.write("### 📋 Contratos Registrados")
        st.dataframe(df_controle, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    aba_gestao_locacao()