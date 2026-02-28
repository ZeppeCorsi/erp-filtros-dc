import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Filtros DC | BI", page_icon="💧", layout="wide")

@st.cache_data
def load_and_clean_data(file_path):
    try:
        # Adicionamos 'sheet_name="Vendas"' para garantir que ele foque na aba correta
        df = pd.read_excel(file_path, engine="openpyxl", sheet_name="Vendas")
        
        # Ajuste dos índices baseado na sua imagem:
        # B(1)=Data, C(2)=Cliente, E(4)=CFOPs, F(5)=faturamento
        df = df.iloc[:, [1, 2, 4, 5]]
        df.columns = ['Data', 'Cliente', 'Tipo', 'Valor']

        # Limpeza de datas
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        df = df.dropna(subset=['Data'])
        
        # Garantir que o ano esteja no range (vimos datas de 2021 e 2026 na sua imagem)
        df = df[(df['Data'].dt.year >= 2010) & (df['Data'].dt.year <= 2030)]
        
        # Limpeza de valores (o 'faturamento' na imagem tem números decimais)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
        
        # Formatação de texto
        df['Cliente'] = df['Cliente'].astype(str).str.upper().str.strip()
        df['Tipo'] = df['Tipo'].astype(str).str.strip()
        
        return df.sort_values('Data')
    except Exception as e:
        st.error(f"Erro ao ler a aba 'Vendas': {e}")
        return pd.DataFrame()

# --- INÍCIO DO APP ---
df_raw = load_and_clean_data("Vendas Gerais.xlsx")

if not df_raw.empty:
    st.title("💧 Filtros DC - Gestão Comercial")

    # --- SIDEBAR (CONFIGURAÇÕES) ---
    st.sidebar.header("Configurações de Filtro")
    
    data_min_cal = df_raw['Data'].min().date()
    data_max_cal = df_raw['Data'].max().date()
    periodo = st.sidebar.date_input("Selecione o Período", [data_min_cal, data_max_cal], format="DD/MM/YYYY")

    opcoes_tipos = sorted(df_raw['Tipo'].unique().tolist())
    tipos_selecionados = st.sidebar.multiselect("Filtrar por Tipo:", options=opcoes_tipos)

    opcoes_clientes = sorted(df_raw['Cliente'].unique().tolist())
    clientes_selecionados = st.sidebar.multiselect("Filtrar por Clientes:", options=opcoes_clientes)

    # --- APLICANDO OS FILTROS ---
    # Proteção: só filtra data se o usuário selecionou o range completo [início, fim]
    if len(periodo) == 2:
        mask_data = (df_raw['Data'].dt.date >= periodo[0]) & (df_raw['Data'].dt.date <= periodo[1])
    else:
        mask_data = True
        
    df_filtered = df_raw[mask_data].copy()

    if tipos_selecionados:
        df_filtered = df_filtered[df_filtered['Tipo'].isin(tipos_selecionados)]
    
    if clientes_selecionados:
        df_filtered = df_filtered[df_filtered['Cliente'].isin(clientes_selecionados)]

    # --- MÉTRICAS ---
    def formato_br(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Faturamento", formato_br(df_filtered['Valor'].sum()))
    m2.metric("Vendas", len(df_filtered))
    m3.metric("Ticket Médio", formato_br(df_filtered['Valor'].mean() if len(df_filtered) > 0 else 0))
    m4.metric("Clientes Ativos", df_filtered['Cliente'].nunique())

    st.markdown("---")

    # --- GRÁFICOS LADO A LADO (AGORA DENTRO DO IF) ---
    col_fat, col_freq = st.columns(2)

    with col_fat:
        st.subheader("🏆 Top Faturamento")
        if not df_filtered.empty:
            top_fat = df_filtered.groupby('Cliente')['Valor'].sum().nlargest(10).reset_index()
            fig1 = px.bar(
                top_fat, x='Valor', y='Cliente', orientation='h', 
                color='Valor', color_continuous_scale='Blues',
                text=top_fat['Valor'].apply(lambda x: f'R$ {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'))
            )
            fig1.update_traces(textposition='outside', cliponaxis=False)
            fig1.update_layout(showlegend=False, coloraxis_showscale=False, height=450)
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.warning("Sem dados para o faturamento.")

    with col_freq:
        st.subheader("🔄 Top Frequência")
        if not df_filtered.empty:
            top_freq = df_filtered.groupby('Cliente')['Data'].count().nlargest(10).reset_index()
            fig2 = px.bar(top_freq, x='Data', y='Cliente', orientation='h', color_discrete_sequence=['#2ecc71'], text_auto=True)
            fig2.update_layout(height=450)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("Sem dados para frequência.")

    # --- TABELA DETALHADA ---
    st.markdown("---")
    st.subheader("📋 Detalhamento das Vendas")
    st.dataframe(
        df_filtered[['Data', 'Cliente', 'Tipo', 'Valor']].sort_values('Data', ascending=False), 
        use_container_width=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "Data": st.column_config.DateColumn("Data da Venda", format="DD/MM/YYYY")
        }
    )
else:
    st.error("O arquivo Excel está vazio ou não pôde ser carregado.")
