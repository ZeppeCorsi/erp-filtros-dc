import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import plotly.express as px

# 1. CONFIGURAÇÃO DA PÁGINA (Sempre o primeiro comando)
st.set_page_config(page_title="Gestão | Filtros DC", layout="wide")

# 2. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Por favor, faça login na página Home.")
    st.stop()

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)

# 3. CONEXÃO OFICIAL (Garante que funcione no Cloud e Local)
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados_gestao():
    try:
        # Lendo via Connection (mais seguro para gravar/ler no Cloud)
        df = conn.read(worksheet="Vendas", ttl=0)
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # TRATAMENTO DE DATA
        if 'DATA' in df.columns:
            df['DATA_DT'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        
        # LIMPEZA DE VALOR (Para os Gráficos)
        def limpar_dinheiro(valor):
            v = str(valor).strip().lower()
            if v in ['nan', 'none', '']: return 0.0
            v = "".join(c for c in v if c.isdigit() or c in [',', '.'])
            if ',' in v and '.' in v: v = v.replace('.', '').replace(',', '.')
            elif ',' in v: v = v.replace(',', '.')
            try: return float(v)
            except: return 0.0

        # Identifica a coluna de faturamento
        col_fat = next((c for c in df.columns if 'TOTAL' in c), None)
        df['VALOR_NUM'] = df[col_fat].apply(limpar_dinheiro) if col_fat else 0.0
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("💰 Gestão de Vendas - Filtros DC")
df_vendas = carregar_dados_gestao()

if df_vendas.empty:
    st.info("Aguardando lançamentos na planilha de Vendas...")
    st.stop()

tab_estudo, tab_info = st.tabs(["📊 Estudo de Vendas", "➕ Info"])

with tab_estudo:
    st.subheader("📅 Filtros de Período e Cliente")
    c1, c2, c3 = st.columns([1, 1, 2])
    
    with c1: dt_ini = st.date_input("Início:", value=date(2024, 1, 1), format="DD/MM/YYYY")
    with c2: dt_fim = st.date_input("Fim:", value=date.today(), format="DD/MM/YYYY")
    
    # Filtro de Cliente unificado
    lista_clientes = ["TODOS"] + sorted(df_vendas["CLIENTE"].dropna().unique().tolist())
    with c3: cliente_sel = st.selectbox("Filtrar por Cliente:", options=lista_clientes)

    # Aplicação dos Filtros
    df_filtrado = df_vendas[
        (df_vendas['DATA_DT'].dt.date >= dt_ini) & 
        (df_vendas['DATA_DT'].dt.date <= dt_fim)
    ].copy()

    if cliente_sel != "TODOS":
        df_filtrado = df_filtrado[df_filtrado["CLIENTE"] == cliente_sel]

    if not df_filtrado.empty:
        # --- MÉTRICAS ---
        total_fat = df_filtrado['VALOR_NUM'].sum()
        total_pedidos = len(df_filtrado)
        
        m1, m2, m3 = st.columns(3)
        valor_formatado = f"R$ {total_fat:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        m1.metric("Faturamento no Período", valor_formatado)
        m2.metric("Qtd. de Pedidos", total_pedidos)
        ticket = total_fat/total_pedidos if total_pedidos > 0 else 0
        m3.metric("Ticket Médio", f"R$ {ticket:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        # --- GRÁFICOS (Só aparecem se for "TODOS" para fazer sentido comparar) ---
        if cliente_sel == "TODOS":
            st.markdown("---")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.write("🏆 **Top 10 Clientes (Faturamento)**")
                top_fat = df_filtrado.groupby('CLIENTE')['VALOR_NUM'].sum().nlargest(10).reset_index()
                fig1 = px.bar(top_fat, x='CLIENTE', y='VALOR_NUM', color='VALOR_NUM', template="plotly_white")
                st.plotly_chart(fig1, use_container_width=True)
            with col_g2:
                st.write("🔄 **Frequência de Compras**")
                top_freq = df_filtrado['CLIENTE'].value_counts().nlargest(10).reset_index()
                top_freq.columns = ['CLIENTE', 'PEDIDOS']
                fig2 = px.pie(top_freq, names='CLIENTE', values='PEDIDOS', hole=0.3)
                st.plotly_chart(fig2, use_container_width=True)

        # --- TABELA DETALHADA (O que você pediu) ---
        st.divider()
        st.subheader(f"🔍 Detalhamento: {cliente_sel}")
        
        # Removendo colunas indesejadas
        colunas_remover = ["COMPRAS", "E PAGAMENTO", "DATA_DT", "VALOR_NUM"]
        df_tabela = df_filtrado.drop(columns=[c for c in colunas_remover if c in df_filtrado.columns])
        
        st.dataframe(df_tabela, use_container_width=True, hide_index=True)
        
    else:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")

with tab_info:
    st.info("Os dados são atualizados em tempo real conforme as vendas são salvas.")