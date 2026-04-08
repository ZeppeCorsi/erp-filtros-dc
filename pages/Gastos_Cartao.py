import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date  # <--- Adicionado 'date'
from dateutil.relativedelta import relativedelta # <--- Adicionado para cálculos de meses
import os

# 1. CONFIGURAÇÕES INICIAIS E PASTAS
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

st.set_page_config(page_title="Gastos Cartão | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÃO DE CARREGAMENTO E CÁLCULO DE SALDO ---
def aba_gastos_cartao():
    st.subheader("💳 Registro de Gastos no Cartão - Filtros DC")
    
    # 1. FORMULÁRIO DE ENTRADA
    with st.form("form_cartao", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_compra = st.date_input("Data da Compra", value=date.today())
            descricao = st.text_input("Descrição do Gasto (ex: Combustível, Peças)")
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
            
        with col2:
            st.info("Configuração da Fatura")
            data_pagamento_fatura = st.date_input("Data de Vencimento da Fatura", value=date.today() + relativedelta(months=1))
            
        btn_salvar = st.form_submit_button("Registrar Gasto")

        if btn_salvar:
            if descricao and valor > 0:
                try:
                    # LEITURA DAS ABAS PARA APPEND (Garante que não sobrescreve)
                    df_cartao_antigo = conn.read(worksheet="Gastos Cartao", ttl=0).dropna(how='all')
                    df_fluxo_antigo = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')

                    # 1. Dados para Aba Gastos Cartao
                    nova_compra = pd.DataFrame([{
                        "DATA": data_compra.strftime("%d/%m/%Y"),
                        "DESCRICAO": descricao.upper(),
                        "VALOR": valor,
                        "PAGAMENTO_FATURA": data_pagamento_fatura.strftime("%d/%m/%Y")
                    }])
                    
                    # 2. Dados para Aba Fluxo de Caixa
                    novo_fluxo = pd.DataFrame([{
                        "DATA": data_pagamento_fatura.strftime("%d/%m/%Y"),
                        "TIPO": "SAIDA",
                        "DESCRICAO": f"CARTAO: {descricao.upper()}",
                        "VALOR": valor,
                        "PARCELA": "1/1",
                        "STATUS": "PENDENTE",
                        "CLIENTE": "FILTROS DC",
                        "NF": "FATURA"
                    }])

                    # SALVAMENTO (Concatena o antigo com o novo)
                    conn.update(worksheet="Gastos Cartao", data=pd.concat([df_cartao_antigo, nova_compra], ignore_index=True))
                    
                    # No Fluxo, garantimos que as colunas batam com as 8 colunas oficiais
                    df_fluxo_final = pd.concat([df_fluxo_antigo, novo_fluxo], ignore_index=True).iloc[:, :8]
                    conn.update(worksheet="Fluxo de Caixa", data=df_fluxo_final)
                    
                    st.success("✅ Gasto registrado e provisionado no Fluxo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Por favor, preencha a descrição e o valor.")

    # 2. VISUALIZAÇÃO (FORA DO FORMULÁRIO)
    st.markdown("---")
    st.subheader("📋 Últimos Lançamentos no Cartão")
    
    df_lista_cartao = conn.read(worksheet="Gastos Cartao", ttl=0)
    
    if df_lista_cartao is not None and not df_lista_cartao.empty:
        # Limpeza para exibição
        df_lista_cartao = df_lista_cartao.dropna(how='all')
        st.dataframe(df_lista_cartao, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum gasto registrado na aba 'Gastos Cartao'.")