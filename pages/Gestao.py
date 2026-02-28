import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import plotly.express as px

# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Por favor, faça login na página Home.")
    st.stop()

# 2. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gestão | Filtros DC", layout="wide")
st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)

# URL DA PLANILHA (A mesma que usamos nas outras páginas)
ID_P = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_VENDAS = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Vendas"

def carregar_vendas_gsheets():
    try:
        # Lendo via link direto CSV para evitar o erro de "Spreadsheet must be specified"
        df = pd.read_csv(URL_VENDAS)
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # TRATAMENTO DE DATA
        if 'DATA' in df.columns:
            df['Data_DT'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        
        # LIMPEZA DE VALOR
        def limpar_dinheiro(valor):
            v = str(valor).strip().lower()
            if v in ['nan', 'none', '']: return 0.0
            v = "".join(c for c in v if c.isdigit() or c in [',', '.'])
            if ',' in v and '.' in v: v = v.replace('.', '').replace(',', '.')
            elif ',' in v: v = v.replace(',', '.')
            try: return float(v)
            except: return 0.0

        col_fat = next((c for c in df.columns if 'TOTAL' in c or 'VALOR' in c), None)
        df['Valor_Num'] = df[col_fat].apply(limpar_dinheiro) if col_fat else 0.0
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("💰 Gestão de Vendas - Filtros DC")
df_vendas = carregar_vendas_gsheets()

tab_estudo, tab_incluir = st.tabs(["📊 Estudo de Vendas", "➕ Info"])

with tab_estudo:
    if not df_vendas.empty:
        st.subheader("📅 Período e Filtros")
        c1, c2 = st.columns(2)
        with c1: dt_ini = st.date_input("Início:", value=date(2024, 1, 1), format="DD/MM/YYYY")
        with c2: dt_fim = st.date_input("Fim:", value=date.today(), format="DD/MM/YYYY")

        df_periodo = df_vendas[(df_vendas['Data_DT'].dt.date >= dt_ini) & 
                               (df_vendas['Data_DT'].dt.date <= dt_fim)].copy()

        if not df_periodo.empty:
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.subheader("🏆 Top 10 Clientes (Faturamento)")
                top_fat = df_periodo.groupby('CLIENTE')['Valor_Num'].sum().nlargest(10).reset_index()
                fig1 = px.bar(top_fat, x='CLIENTE', y='Valor_Num', color='Valor_Num', template="plotly_white")
                st.plotly_chart(fig1, use_container_width=True)

            with col_graf2:
                st.subheader("🔄 Frequência por Cliente")
                top_freq = df_periodo['CLIENTE'].value_counts().nlargest(10).reset_index()
                top_freq.columns = ['CLIENTE', 'PEDIDOS']
                fig2 = px.pie(top_freq, names='CLIENTE', values='PEDIDOS', hole=0.3)
                st.plotly_chart(fig2, use_container_width=True)

            st.divider()
            st.subheader("🔍 Extrato Detalhado")
            st.dataframe(df_periodo[['DATA', 'CLIENTE', 'PRODUTO', 'TOTAL', 'VENDEDOR']], use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum dado encontrado para estas datas.")
    else:
        st.info("Aguardando lançamentos na planilha de Vendas...")

with tab_incluir:
    st.info("As vendas são registradas na página 'Vendas' e aparecem aqui automaticamente.")