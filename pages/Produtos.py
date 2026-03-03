import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser o primeiro comando Streamlit)
st.set_page_config(page_title="Estoque | Filtros DC", layout="wide")

# 2. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

# 3. CONEXÃO (ID Mestre da sua planilha)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados_limpos():
    try:
        # Lendo a aba Produtos usando a URL mestre para garantir acesso
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet="Produtos", ttl=0)
        
        # Limpeza de colunas
        df.columns = [str(c).strip().upper() for c in df.columns]
        # Limpeza de espaços em branco nas células
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        
        # Tratamento do código para evitar o erro de "item não encontrado"
        if 'CODIGO' in df.columns:
            df['CODIGO'] = df['CODIGO'].astype(str).str.replace('.0', '', regex=False)
            
        return df
    except Exception as e:
        st.error(f"⚠️ Erro ao acessar Google Sheets: {e}")
        st.info("Dica: Verifique se a planilha está compartilhada como 'Editor' para 'Qualquer pessoa com o link'.")
        return pd.DataFrame()

# --- CARREGAMENTO INICIAL ---
df_estoque = carregar_dados_limpos()

# --- INTERFACE ---
st.title("📦 Controle de Estoque - Filtros DC")

aba1, aba2 = st.tabs(["📋 Saldo em Estoque", "➕ Cadastrar Novo Item"])

with aba1:
    if not df_estoque.empty:
        busca = st.text_input("🔍 Buscar produto...")
        # Filtro de busca inteligente
        df_filtrado = df_estoque[df_estoque.apply(lambda r: r.astype(str).str.contains(busca, case=False).any(), axis=1)] if busca else df_estoque
        
        # Lógica de perfil (ADM / VENDEDOR)
        perfil = str(st.session_state.get('perfil', 'VENDEDOR')).upper()
        col_ocultar = ["CUSTO TOTAL", "MARKUP"] if perfil != "ADM" else []
        df_para_mostrar = df_filtrado.drop(columns=[c for c in col_ocultar if c in df_filtrado.columns])
        
        st.dataframe(df_para_mostrar, use_container_width=True, hide_index=True)
    else:
        st.warning("Aguardando dados da planilha...")

# --- CENTRAL DE MONTAGEM ---
st.markdown("---")
st.header("🛠️ Central de Montagem de Kits")

FORMULAS = {
    "5001": {"3001": 6.3, "3002": 4.3, "3003": 4.3, "3004": 4.3, "3005": 6.3, "3006": 1.0},
    "5002": {"3001": 10.2, "3002": 8.2, "3003": 8.2, "3004": 8.2, "3005": 8.2, "3006": 1.8},
    "5003": {"3001": 19.0, "3002": 13.5, "3003": 13.5, "3004": 13.5, "3005": 18.0, "3006": 2.5},
    "5004": {"3001": 26.5, "3002": 18.5, "3003": 18.5, "3004": 18.5, "3005": 25.5, "3006": 3.4},
    "5005": {"3001": 57.0, "3002": 38.0, "3003": 38.0, "3004": 38.0, "3005": 53.0, "3006": 7.0},
    "5006": {"3001": 120.0, "3002": 80.0, "3003": 80.0, "3004": 80.0, "3005": 120.0, "3006": 15.0}
}

# Criar lista de nomes para o selectbox
opcoes_montagem = {}
if not df_estoque.empty:
    for cod_f in FORMULAS.keys():
        match = df_estoque[df_estoque['CODIGO'] == str(cod_f)]
        nome = match['NOME'].values[0] if not match.empty else "Item não localizado"
        opcoes_montagem[f"{cod_f} - {nome}"] = cod_f

with st.container(border=True):
    c1, c2 = st.columns([2, 1])
    with c1:
        label_selecionado = st.selectbox("Produto para Montar:", options=list(opcoes_montagem.keys()))
        item_escolhido = opcoes_montagem[label_selecionado]
    with c2:
        qtd_montar = st.number_input("Quantidade de Kits:", min_value=1, value=1)

    if st.button("🚀 Executar Montagem e Atualizar Google Sheets"):
        df_novo = carregar_dados_limpos()
        if not df_novo.empty:
            df_novo['ESTOQUE'] = pd.to_numeric(df_novo['ESTOQUE'], errors='coerce').fillna(0)
            
            receita = FORMULAS[item_escolhido]
            erros = []

            # Validação
            for cod, qtd in receita.items():
                precisa = qtd * qtd_montar
                linha = df_novo[df_novo['CODIGO'] == str(cod)]
                if linha.empty:
                    erros.append(f"❌ Código {cod} não existe na planilha.")
                elif linha['ESTOQUE'].values[0] < precisa:
                    erros.append(f"⚠️ {cod}: Saldo insuficiente ({linha['ESTOQUE'].values[0]} < {precisa}).")

            if erros:
                for err in erros: st.error(err)
            else:
                # Execução
                for cod, qtd in receita.items():
                    df_novo.loc[df_novo['CODIGO'] == str(cod), 'ESTOQUE'] -= (qtd * qtd_montar)
                
                df_novo.loc[df_novo['CODIGO'] == str(item_escolhido), 'ESTOQUE'] += qtd_montar
                
                # Update oficial
                conn.update(spreadsheet=URL_PLANILHA, worksheet="Produtos", data=df_novo)
                st.success("✅ Estoque atualizado com sucesso!")
                st.balloons()
                st.rerun()

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)