import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Financeiro | Filtros DC", layout="wide")

if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Faça o login na home.")
    st.stop()

conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- PROCESSAMENTO DE DADOS (VERSÃO BLINDADA) ---
# --- PROCESSAMENTO DE DADOS (LIMPEZA PROFUNDA) ---
try:
    df_fluxo_raw = conn.read(worksheet="Fluxo de Caixa", ttl=0)
    df_gastos_raw = conn.read(worksheet="Gastos Fixos", ttl=0)

    # 1. Padronização do Fluxo
    df_fluxo = df_fluxo_raw.copy()
    df_fluxo.columns = [str(c).strip().upper() for c in df_fluxo.columns]

    # CORREÇÃO DO ERRO 'UPPER': Força conversão para string em cada célula
    df_fluxo['TIPO'] = df_fluxo['TIPO'].fillna('').astype(str).apply(lambda x: x.strip().upper())
    df_fluxo['STATUS'] = df_fluxo['STATUS'].fillna('').astype(str).apply(lambda x: x.strip().upper())
    
    if 'DESCRICAO' not in df_fluxo.columns:
        df_fluxo['DESCRICAO'] = ""

    # Conversão de Valores
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)

    # Datas e Meses
    df_fluxo['DT_OBJ'] = pd.to_datetime(df_fluxo['DATA'], dayfirst=True, errors='coerce')
    df_fluxo = df_fluxo.dropna(subset=['DT_OBJ']).sort_values('DT_OBJ')
    df_fluxo['MES_REF'] = df_fluxo['DT_OBJ'].dt.strftime('%m/%Y')

    # --- MATEMÁTICA DO SALDO (SUBTRAÇÃO REAL) ---
    # Somamos apenas ENTRADA que foi RECEBIDO
    total_entradas = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    
    # Somamos apenas SAIDA que foi PAGO (ou RECEBIDO, dependendo de como você marca)
    # Dica: Se no seu fluxo a saída paga está como 'RECEBIDO' ou 'PAGO', ajuste aqui:
    total_saidas = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & 
                            ((df_fluxo['STATUS'] == 'PAGO') | (df_fluxo['STATUS'] == 'RECEBIDO'))]['VALOR'].sum()
    
    saldo_real_conta = total_entradas - total_saidas

    # --- INTERFACE ---
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    meses_opcoes = ["Tudo"] + sorted(df_fluxo['MES_REF'].unique().tolist(), key=lambda x: datetime.strptime(x, '%m/%Y'))
    filtro_mes = st.selectbox("Selecione o período:", meses_opcoes, index=len(meses_opcoes)-1)
    df_periodo = df_fluxo if filtro_mes == "Tudo" else df_fluxo[df_fluxo['MES_REF'] == filtro_mes]

    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo Real (Hoje)", f"R$ {saldo_real_conta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    ent_p = df_periodo[(df_periodo['TIPO'] == 'ENTRADA') & (df_periodo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    sai_p = df_periodo[(df_periodo['TIPO'] == 'SAIDA') & 
                       ((df_periodo['STATUS'] == 'PAGO') | (df_periodo['STATUS'] == 'RECEBIDO'))]['VALOR'].sum()
    
    c2.metric(f"Entradas ({filtro_mes})", f"R$ {ent_p:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric(f"Saídas ({filtro_mes})", f"- R$ {sai_p:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")

    st.divider()

    # --- TABELA COM SINAL DE MENOS ---
    st.subheader(f"Extrato: {filtro_mes}")
    
    def formatar_tabela(linha):
        v = linha['VALOR']
        if linha['TIPO'] == 'SAIDA':
            return f"- R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    df_viz = df_periodo[['DATA', 'TIPO', 'CLIENTE', 'DESCRICAO', 'VALOR', 'STATUS', 'NF']].copy()
    df_viz['VALOR'] = df_viz.apply(formatar_tabela, axis=1)
    st.dataframe(df_viz, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro ao processar: {e}")