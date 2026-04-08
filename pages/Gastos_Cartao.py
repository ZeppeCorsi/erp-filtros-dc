import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import os

# 1. CONFIGURAÇÕES INICIAIS E PASTAS
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

# Configuração de página deve ser a primeira coisa após os imports
# st.set_page_config(page_title="Gastos Cartão | Filtros DC", layout="wide") # Se já houver no main.py, comente esta linha

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÃO DE CARREGAMENTO ---
def aba_gastos_cartao():
    st.subheader("💳 Gestão de Cartão de Crédito - Filtros DC")
    
    # --- CONFIGURAÇÃO DO CARTÃO ---
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        dia_fechamento = st.number_input("Dia de Fechamento (ex: 28)", min_value=1, max_value=31, value=28)
    with col_cfg2:
        dia_vencimento = st.number_input("Dia de Vencimento (ex: 05)", min_value=1, max_value=31, value=5)

    # --- 1. NOVO GASTO ---
    with st.expander("➕ Registrar Novo Gasto Individual", expanded=True):
        with st.form("form_cartao", clear_on_submit=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            data_compra = c1.date_input("Data", value=date.today())
            desc = c2.text_input("Descrição")
            valor = c3.number_input("Valor (R$)", min_value=0.0, step=0.01)
            
            if st.form_submit_button("Adicionar ao Cartão"):
                if desc and valor > 0:
                    df_antigo = conn.read(worksheet="Gastos Cartao", ttl=0).dropna(how='all')
                    nova_linha = pd.DataFrame([{"DATA": data_compra.strftime("%d/%m/%Y"), "DESCRICAO": desc.upper(), "VALOR": valor, "STATUS": "ABERTO"}])
                    conn.update(worksheet="Gastos Cartao", data=pd.concat([df_antigo, nova_linha], ignore_index=True))
                    st.success("Gasto adicionado!")
                    st.rerun()

    # --- 2. RESUMO E FECHAMENTO ---
    st.markdown("---")
    df_cartao = conn.read(worksheet="Gastos Cartao", ttl=0).dropna(how='all')
    
    if not df_cartao.empty:
        # Filtra apenas o que está "ABERTO" (não foi para o fluxo ainda)
        df_aberto = df_cartao[df_cartao["STATUS"] == "ABERTO"]
        total_fatura = df_aberto["VALOR"].sum()
        
        col_res1, col_res2 = st.columns([2, 1])
        col_res1.metric("Valor Total da Fatura Atual", f"R$ {total_fatura:,.2f}")
        
        with col_res2:
            if total_fatura > 0:
                if st.button("🚀 FECHAR FATURA E LANÇAR NO FLUXO"):
                    # Calcula data de vencimento (Próximo mês, no dia escolhido)
                    vencimento_fatura = (date.today() + relativedelta(months=1)).replace(day=dia_vencimento)
                    
                    # 1. Lança no Fluxo de Caixa como uma saída única
                    df_fluxo_antigo = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
                    novo_fluxo = pd.DataFrame([{
                        "DATA": vencimento_fatura.strftime("%d/%m/%Y"),
                        "TIPO": "SAIDA",
                        "DESCRICAO": f"FECHAMENTO CARTÃO - {date.today().strftime('%m/%Y')}",
                        "VALOR": total_fatura,
                        "PARCELA": "1/1",
                        "STATUS": "PENDENTE",
                        "CLIENTE": "FILTROS DC",
                        "NF": "FATURA"
                    }])
                    
                    # 2. Atualiza os gastos do cartão para "FECHADO"
                    df_cartao.loc[df_cartao["STATUS"] == "ABERTO", "STATUS"] = "FECHADO"
                    
                    # Salva ambos
                    conn.update(worksheet="Fluxo de Caixa", data=pd.concat([df_fluxo_antigo, novo_fluxo], ignore_index=True).iloc[:, :8])
                    conn.update(worksheet="Gastos Cartao", data=df_cartao)
                    
                    st.success(f"Fatura de R$ {total_fatura:.2f} lançada para {vencimento_fatura.strftime('%d/%m/%Y')}!")
                    st.rerun()

        # --- 3. TABELA DE DETALHES ---
        st.subheader("📋 Itens na Fatura Aberta")
        st.dataframe(df_aberto, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum gasto em aberto no cartão.")
        
# --- 3. EXECUÇÃO DA FUNÇÃO ---
# ESTA LINHA É O QUE FAZ O CÓDIGO APARECER
aba_gastos_cartao()