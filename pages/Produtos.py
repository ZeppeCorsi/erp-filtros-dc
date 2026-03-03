import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Estoque | Filtros DC", layout="wide")

# 2. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado!")
    st.stop()

# 3. CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados_produtos():
    try:
        # Lendo a aba Produtos. O ttl=0 evita pegar dados velhos do cache.
        df = conn.read(worksheet="Produtos", ttl=0)
        
        # PADRONIZAÇÃO RADICAL:
        # Remove colunas vazias que o Google às vezes gera à direita
        df = df.dropna(how='all', axis=1)
        # Limpa nomes de colunas
        df.columns = [str(c).strip().upper() for c in df.columns]
        # Garante que CODIGO seja string e ESTOQUE seja número
        if 'CODIGO' in df.columns:
            df['CODIGO'] = df['CODIGO'].astype(str).str.replace('.0', '', regex=False).str.strip()
        if 'ESTOQUE' in df.columns:
            df['ESTOQUE'] = pd.to_numeric(df['ESTOQUE'], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"Erro ao ler planilha: {e}")
        return pd.DataFrame()

# --- CARGA DOS DADOS ---
df_estoque = carregar_dados_produtos()

st.title("📦 Controle de Estoque - Filtros DC")

if df_estoque.empty:
    st.warning("⚠️ Não foi possível carregar a tabela 'Produtos'.")
    st.stop()

aba1, aba2 = st.tabs(["📋 Saldo em Estoque", "➕ Cadastrar Novo Item"])

with aba1:
    busca = st.text_input("🔍 Buscar produto...")
    df_filtrado = df_estoque[df_estoque.apply(lambda r: r.astype(str).str.contains(busca, case=False).any(), axis=1)] if busca else df_estoque
    
    perfil = str(st.session_state.get('perfil', 'VENDEDOR')).upper()
    col_ocultar = ["CUSTO TOTAL", "MARKUP"] if perfil != "ADM" else []
    df_para_mostrar = df_filtrado.drop(columns=[c for c in col_ocultar if c in df_filtrado.columns])
    
    st.dataframe(df_para_mostrar, use_container_width=True, hide_index=True)

# --- CENTRAL DE MONTAGEM ---
st.markdown("---")
st.header("🛠️ Central de Montagem de Kits")

# 1. DEFINIÇÃO DAS RECEITAS (IDs como String)
FORMULAS = {
    # --- FILTROS COMPLETOS (Vaso + Kit Quartzo) ---
    "1001": {"2001": 1, "5001": 1},
    "1002": {"2002": 1, "5002": 1},
    "1003": {"2003": 1, "5003": 1},
    "1004": {"2004": 1, "5004": 1},
    "1005": {"2005": 1, "5005": 1},
    "1006": {"2006": 1, "5006": 1},
    
    # --- KITS DE QUARTZO/CARVÃO ---
    "5001": {"3001": 6.3, "3002": 4.3, "3003": 4.3, "3004": 4.3, "3005": 6.3, "3006": 1.0},
    "5002": {"3001": 10.2, "3002": 8.2, "3003": 8.2, "3004": 8.2, "3005": 8.2, "3006": 1.8},
    "5003": {"3001": 19.0, "3002": 13.5, "3003": 13.5, "3004": 13.5, "3005": 18.0, "3006": 2.5},
    "5004": {"3001": 26.5, "3002": 18.5, "3003": 18.5, "3004": 18.5, "3005": 25.5, "3006": 3.4},
    "5005": {"3001": 57.0, "3002": 38.0, "3003": 38.0, "3004": 38.0, "3005": 53.0, "3006": 7.0},
    "5006": {"3001": 120.0, "3002": 80.0, "3003": 80.0, "3004": 80.0, "3005": 120.0, "3006": 15.0}
}

with st.container(border=True):
    c1, c2 = st.columns([2, 1])
    with c1:
        # Criamos o label "Codigo - Nome" dinamicamente
        opcoes = {}
        for c in FORMULAS.keys():
            match = df_estoque[df_estoque['CODIGO'] == c]
            nome = match['NOME'].values[0] if not match.empty else "NOME NÃO ENCONTRADO"
            opcoes[f"{c} - {nome}"] = c
            
        escolhido = st.selectbox("Escolha o Kit:", options=list(opcoes.keys()))
        cod_kit = opcoes[escolhido]
        
    with c2:
        qtd = st.number_input("Quantidade:", min_value=1, value=1)

    if st.button("🚀 Executar Montagem"):
        # 1. Criar cópia dos dados para processar
        df_atualizado = df_estoque.copy()
        receita = FORMULAS[cod_kit]
        
        # 2. Processar cálculos
        try:
            for item_comp, fator in receita.items():
                reducao = fator * qtd
                df_atualizado.loc[df_atualizado['CODIGO'] == item_comp, 'ESTOQUE'] -= reducao
            
            df_atualizado.loc[df_atualizado['CODIGO'] == cod_kit, 'ESTOQUE'] += qtd
            
            # 3. LIMPEZA FINAL ANTES DE ENVIAR (Para evitar o Erro 400)
            # Converte tudo para string ou formatos simples, removendo NaNs
            df_enviar = df_atualizado.fillna("")
            
            # 4. GRAVAR
            conn.update(worksheet="Produtos", data=df_enviar)
            st.success("✅ Estoque atualizado no Google Sheets!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro no processamento: {e}")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)