import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
from dateutil.relativedelta import relativedelta

def aba_gestao_locacao():
    st.subheader("📑 Gestão de Locação - Filtros DC")
    
    # 1. CONEXÃO SEGURA
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"Erro de conexão com Google Sheets: {e}")
        return # Para a execução aqui para não dar tela branca

    # 2. LEITURA INICIAL (Com tratamento de erro individual)
    try:
        df_clientes = conn.read(worksheet="Clientes", ttl=0)
    except:
        st.warning("Aba 'Clientes' não encontrada.")
        df_clientes = pd.DataFrame(columns=["NOME REDUZIDO"])

    try:
        df_produtos = conn.read(worksheet="Produtos", ttl=0)
    except:
        st.warning("Aba 'Produtos' não encontrada.")
        df_produtos = pd.DataFrame(columns=["NOME", "CUSTO TOTAL"])

    # --- FORMULÁRIO ---
    with st.form("nova_locacao", clear_on_submit=True):
        st.markdown("### Registrar Contrato e Gerar Parcelas Futuras")
        col1, col2 = st.columns(2)
        
        with col1:
            data_ini = st.date_input("Data Original do Contrato", value=date.today())
            
            # Garante que a lista não quebre se o DF estiver vazio
            opcoes_cli = sorted(df_clientes["NOME REDUZIDO"].dropna().unique().tolist()) if not df_clientes.empty else []
            cliente = st.selectbox("Cliente", options=opcoes_cli)
            
            opcoes_prod = sorted(df_produtos["NOME"].dropna().unique().tolist()) if not df_produtos.empty else []
            produto = st.selectbox("Equipamento (Filtro)", options=opcoes_prod)
            
        with col2:
            valor_mensal = st.number_input("Valor Mensal (R$)", min_value=0.0, format="%.2f")
            qtd_para_lancar = st.number_input("Quantas parcelas lançar (a partir de hoje)?", min_value=1, value=12)
            
            # Cálculo de custo seguro
            custo_total = 0.0
            if not df_produtos.empty and produto:
                busca = df_produtos.loc[df_produtos["NOME"] == produto, "CUSTO TOTAL"]
                if not busca.empty:
                    custo_total = float(busca.values[0])
            st.info(f"Custo de Aquisição: R$ {custo_total:,.2f}")

        if st.form_submit_button("Gerar Locação e Lançamentos"):
            if not cliente or not produto:
                st.warning("Selecione um cliente e um produto.")
            else:
                try:
                    # Lendo bases para salvamento
                    df_loc_atual = conn.read(worksheet="Locacao", ttl=0).dropna(how='all')
                    df_fluxo_antigo = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
                    df_vendas_antigo = conn.read(worksheet="Vendas", ttl=0).dropna(how='all')

                    # A) Aba Locacao
                    nova_linha_loc = pd.DataFrame([{
                        "DATA_INICIO": data_ini.strftime("%d/%m/%Y"),
                        "CLIENTE": cliente,
                        "EQUIPAMENTO": produto,
                        "VALOR_MENSAL": valor_mensal,
                        "CUSTO_ORIGINAL": custo_total,
                        "TOTAL_PARCELAS": qtd_para_lancar
                    }])
                    conn.update(worksheet="Locacao", data=pd.concat([df_loc_atual, nova_linha_loc], ignore_index=True))

                    # B) Parcelas a partir de HOJE
                    novas_vendas = []
                    novos_fluxos = []
                    hoje = date.today()

                    for i in range(1, int(qtd_para_lancar) + 1):
                        vencimento = (hoje + relativedelta(months=i-1)).replace(day=5)
                        dt_str = vencimento.strftime("%d/%m/%Y")
                        
                        novos_fluxos.append({
                            "DATA": dt_str, "TIPO": "ENTRADA", "DESCRICAO": f"LOCACAO - {produto}",
                            "VALOR": valor_mensal, "PARCELA": f"{i}/{qtd_para_lancar}", 
                            "STATUS": "PENDENTE", "CLIENTE": cliente, "NF": "LOC"
                        })

                        novas_vendas.append({
                            "NF": "LOC", "DATA": dt_str, "CLIENTE": cliente, "PRODUTO": produto,
                            "CFOPS": "LOC", "TOTAL": valor_mensal, "COMPRAS": 0,
                            "FORMA DE PAGAMENTO": "BOLETO/LOC", "QTD": 1, "VALOR UNIT": valor_mensal,
                            "VENDEDOR": "SISTEMA", "OBS": f"Parc {i}/{qtd_para_lancar}", 
                            "CUSTO": 0, "MARGEM": valor_mensal
                        })
                    
                    # C) Envio consolidado
                    df_f_final = pd.concat([df_fluxo_antigo, pd.DataFrame(novos_fluxos)], ignore_index=True)
                    conn.update(worksheet="Fluxo de Caixa", data=df_f_final.iloc[:, :8])
                    
                    df_v_final = pd.concat([df_vendas_antigo, pd.DataFrame(novas_vendas)], ignore_index=True)
                    conn.update(worksheet="Vendas", data=df_v_final.iloc[:, :14])

                    st.success("✅ Lançamentos realizados com sucesso!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Erro durante a gravação: {e}")

    # --- LISTAGEM FINAL ---
    st.markdown("---")
    try:
        df_vis = conn.read(worksheet="Locacao", ttl=0)
        if df_vis is not None:
            st.write("### 📋 Contratos Registrados")
            st.dataframe(df_vis, use_container_width=True, hide_index=True)
    except:
        st.info("Aba 'Locacao' ainda não contém dados.")

# Execução (Se for arquivo único)
if __name__ == "__main__":
    if 'logado' in st.session_state and st.session_state.logado:
        aba_gestao_locacao()
    else:
        st.warning("Realize o login na página principal.")