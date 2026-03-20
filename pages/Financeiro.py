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
# --- PROCESSAMENTO DE DADOS ---
try:
    df_fluxo_raw = conn.read(worksheet="Fluxo de Caixa", ttl=0)
    
    # Limpeza e Padronização das Colunas
    df_fluxo = df_fluxo_raw.copy()
    df_fluxo.columns = [str(c).strip().upper() for c in df_fluxo.columns]
    
    # Garante que a coluna DESCRICAO existe
    if 'DESCRICAO' not in df_fluxo.columns:
        df_fluxo['DESCRICAO'] = ""

    # Tratamento de Valores e Categorias (Crucial para a soma)
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
    df_fluxo['TIPO'] = df_fluxo['TIPO'].astype(str).str.strip().upper()
    df_fluxo['STATUS'] = df_fluxo['STATUS'].astype(str).str.strip().upper()
    
    # Tratamento de Datas
    df_fluxo['DT_OBJ'] = pd.to_datetime(df_fluxo['DATA'], dayfirst=True, errors='coerce')
    df_fluxo = df_fluxo.dropna(subset=['DT_OBJ']).sort_values('DT_OBJ')
    df_fluxo['MES_REF'] = df_fluxo['DT_OBJ'].dt.strftime('%m/%Y')

    # --- A MÁGICA DA MATEMÁTICA (SOMA vs SUBTRAÇÃO) ---
    # 1. Filtramos apenas o que já foi concretizado (RECEBIDO ou PAGO)
    entradas_confirmadas = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    saidas_confirmadas = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    
    # 2. O Saldo Real é a SUBTRAÇÃO
    saldo_real_hoje = entradas_confirmadas - saidas_confirmadas

    # --- DASHBOARD ---
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    # Filtro de Mês
    meses = ["Tudo"] + sorted(df_fluxo['MES_REF'].unique().tolist(), key=lambda x: datetime.strptime(x, '%m/%Y'))
    mes_selecionado = st.selectbox("Selecione o período:", meses, index=len(meses)-1)
    
    df_periodo = df_fluxo if mes_selecionado == "Tudo" else df_fluxo[df_fluxo['MES_REF'] == mes_selecionado]

    # Métricas Visuais
    m1, m2, m3 = st.columns(3)
    m1.metric("Saldo Real (Conta)", f"R$ {saldo_real_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # Métricas do período filtrado
    ent_p = df_periodo[(df_periodo['TIPO'] == 'ENTRADA') & (df_periodo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    sai_p = df_periodo[(df_periodo['TIPO'] == 'SAIDA') & (df_periodo['STATUS'] == 'PAGO')]['VALOR'].sum()
    
    m2.metric(f"Entradas ({mes_selecionado})", f"R$ {ent_p:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    # Note o sinal de menos aqui
    m3.metric(f"Saídas ({mes_selecionado})", f"- R$ {sai_p:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")

    st.divider()

    # --- TABELA DE EXTRATO COM DESCRICAO ---
    st.subheader(f"Movimentações: {mes_selecionado}")
    
    def formatar_tabela(linha):
        v = linha['VALOR']
        if linha['TIPO'] == 'SAIDA':
            return f"- R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Exibindo com a coluna DESCRICAO
    df_visual = df_periodo[['DATA', 'TIPO', 'CLIENTE', 'DESCRICAO', 'VALOR', 'STATUS', 'NF']].copy()
    df_visual['VALOR'] = df_visual.apply(formatar_tabela, axis=1)
    
    st.dataframe(df_visual, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro crítico: {e}")