import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import plotly.express as px # Usaremos plotly para gráficos mais bonitos

# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Por favor, faça login na página Home.")
    st.stop()

# 2. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gestão | Filtros DC", layout="wide")
st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)

# Conexão com GSheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_vendas_gsheets():
    try:
        # Lê a aba "Vendas" do Google Sheets
        df = conn.read(worksheet="Vendas", ttl=2)
        df.columns = [str(c).strip() for c in df.columns]
        
        # TRATAMENTO DE DATA
        if 'DATA' in df.columns:
            df['Data_DT'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        
        # --- LIMPEZA DE VALOR ---
        def limpar_dinheiro(valor):
            v = str(valor).strip().lower()
            if v in ['nan', 'none', '']: return 0.0
            v = "".join(c for c in v if c.isdigit() or c in [',', '.'])
            if ',' in v and '.' in v:
                v = v.replace('.', '').replace(',', '.')
            elif ',' in v:
                v = v.replace(',', '.')
            try:
                return float(v)
            except:
                return 0.0

        # Mapeia a coluna de faturamento (pode estar como 'TOTAL' ou 'VALOR TOTAL' na sua planilha)
        col_fat = next((c for c in df.columns if 'TOTAL' in c or 'VALOR' in c), None)
        
        if col_fat:
            df['Valor_Num'] = df[col_fat].apply(limpar_dinheiro)
        else:
            df['Valor_Num'] = 0.0
            
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("💰 Gestão de Vendas - Filtros DC")
df_vendas = carregar_vendas_gsheets()

tab_estudo, tab_incluir = st.tabs(["📊 Estudo de Vendas", "➕ Incluir Nova Venda"])

with tab_estudo:
    if not df_vendas.empty:
        st.subheader("📅 Período e Filtros")
        c1, c2 = st.columns(2)
        with c1: dt_ini = st.date_input("Início:", value=date(2024, 1, 1), format="DD/MM/YYYY")
        with c2: dt_fim = st.date_input("Fim:", value=date.today(), format="DD/MM/YYYY")

        # Filtro por data
        df_periodo = df_vendas[(df_vendas['Data_DT'].dt.date >= dt_ini) & 
                               (df_vendas['Data_DT'].dt.date <= dt_fim)].copy()

        if not df_periodo.empty:
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.subheader("🏆 Top 10 Clientes (Faturamento)")
                # Agrupa por cliente e soma o valor numérico
                top_fat = df_periodo.groupby('CLIENTE')['Valor_Num'].sum().nlargest(10).reset_index()
                fig1 = px.bar(top_fat, x='CLIENTE', y='Valor_Num', text_auto='.2s', color='Valor_Num')
                st.plotly_chart(fig1, use_container_width=True)

            with col_graf2:
                st.subheader("🔄 Frequência de Pedidos")
                top_freq = df_periodo['CLIENTE'].value_counts().nlargest(10).reset_index()
                top_freq.columns = ['CLIENTE', 'PEDIDOS']
                fig2 = px.pie(top_freq, names='CLIENTE', values='PEDIDOS', hole=0.3)
                st.plotly_chart(fig2, use_container_width=True)

            # --- ANÁLISE DETALHADA ---
            st.markdown("---")
            st.subheader("🔍 Detalhar um Cliente")
            lista_cli = sorted(df_periodo['CLIENTE'].dropna().unique().tolist())
            cliente_sel = st.selectbox("Selecione para ver o extrato:", ["TODOS"] + lista_cli)
            
            df_final = df_periodo if cliente_sel == "TODOS" else df_periodo[df_periodo['CLIENTE'] == cliente_sel]

            total_v = df_final['Valor_Num'].sum()
            st.metric(f"Faturamento: {cliente_sel}", f"R$ {total_v:,.2f}")

            # Exibição da Tabela
            st.dataframe(df_final[['DATA', 'CLIENTE', 'PRODUTO', 'QTD', 'Valor_Num', 'VENDEDOR']], 
                         use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum dado encontrado para as datas selecionadas.")
    else:
        st.info("Aguardando dados da planilha 'Vendas'...")

with tab_incluir:
    st.info("💡 Dica: Utilize a página 'Lançar Venda' no menu lateral para registrar novos pedidos. Os dados aparecerão aqui automaticamente após o registro.")