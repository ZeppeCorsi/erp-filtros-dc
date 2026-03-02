import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

st.set_page_config(page_title="Estoque | Filtros DC", layout="wide")

# 2. CONFIGURAÇÃO DE CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados_limpos():
    # Lendo direto via connection para garantir compatibilidade com o update depois
    df = conn.read(worksheet="Produtos", ttl=0)
    # Limpeza profunda: nomes de colunas sem espaços e em maiúsculo
    df.columns = [str(c).strip().upper() for c in df.columns]
    # Limpeza de dados: remove espaços de todas as células de texto
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    # Garante que CODIGO seja sempre string limpa
    if 'CODIGO' in df.columns:
        df['CODIGO'] = df['CODIGO'].astype(str).str.replace('.0', '', regex=False)
    return df

# --- INTERFACE ---
st.title("📦 Controle de Estoque - Filtros DC")
df_estoque = carregar_dados_limpos()

aba1, aba2 = st.tabs(["📋 Saldo em Estoque", "➕ Cadastrar Novo Item"])

with aba1:
    if not df_estoque.empty:
        busca = st.text_input("🔍 Buscar produto...")
        df_filtrado = df_estoque[df_estoque.apply(lambda r: r.astype(str).str.contains(busca, case=False).any(), axis=1)] if busca else df_estoque
        
        # Lógica de perfil (ADM / VENDEDOR)
        perfil = str(st.session_state.get('perfil', 'VENDEDOR')).upper()
        col_ocultar = ["CUSTO TOTAL", "MARKUP"] if perfil != "ADM" else []
        df_para_mostrar = df_filtrado.drop(columns=[c for c in col_ocultar if c in df_filtrado.columns])
        
        st.dataframe(df_para_mostrar, use_container_width=True, hide_index=True)
    else:
        st.warning("Planilha vazia ou não encontrada.")

# --- CENTRAL DE MONTAGEM (CÓDIGO FINAL E INTEGRADO) ---
st.markdown("---")
st.header("🛠️ Central de Montagem de Kits")

# 1. DEFINIÇÃO DAS RECEITAS (IDs como String)
FORMULAS = {
    "5001": {"3001": 6.3, "3002": 4.3, "3003": 4.3, "3004": 4.3, "3005": 6.3, "3006": 1.0},
    "5002": {"3001": 10.2, "3002": 8.2, "3003": 8.2, "3004": 8.2, "3005": 8.2, "3006": 1.8},
    "5003": {"3001": 19.0, "3002": 13.5, "3003": 13.5, "3004": 13.5, "3005": 18.0, "3006": 2.5},
    "5004": {"3001": 26.5, "3002": 18.5, "3003": 18.5, "3004": 18.5, "3005": 25.5, "3006": 3.4},
    "5005": {"3001": 57.0, "3002": 38.0, "3003": 38.0, "3004": 38.0, "3005": 53.0, "3006": 7.0},
    "5006": {"3001": 120.0, "3002": 80.0, "3003": 80.0, "3004": 80.0, "3005": 120.0, "3006": 15.0}
}

# 2. PREPARAR LISTA DINÂMICA (CÓDIGO - NOME)
opcoes_selectbox = {}
for cod_f in FORMULAS.keys():
    # Busca o nome no df_estoque que já foi carregado no início da sua página
    match = df_estoque[df_estoque['CODIGO'] == str(cod_f)]
    if not match.empty:
        nome_completo = f"{cod_f} - {match['NOME'].values[0]}"
        opcoes_selectbox[nome_completo] = cod_f
    else:
        opcoes_selectbox[f"{cod_f} - (Item não localizado)"] = cod_f

# 3. INTERFACE DE USUÁRIO
with st.container(border=True):
    col_sel, col_qtd = st.columns([2, 1])
    
    with col_sel:
        label_escolhido = st.selectbox("Selecione o Kit para Montagem:", options=list(opcoes_selectbox.keys()))
        # Recupera apenas o código (ex: "5001") para o processamento
        id_final = opcoes_selectbox[label_escolhido]
        
    with col_qtd:
        qtd_montar = st.number_input("Quantidade de Kits:", min_value=1, value=1, step=1)

    if st.button("🚀 Confirmar Montagem e Atualizar Estoque"):
        # Lemos a planilha em tempo real para evitar erros de saldo
        df_atual = carregar_dados_limpos() 
        df_atual['ESTOQUE'] = pd.to_numeric(df_atual['ESTOQUE'], errors='coerce').fillna(0)
        
        receita = FORMULAS[id_final]
        pode_prosseguir = True
        erros = []

        # A. VALIDAÇÃO DE SEGURANÇA
        for componente, proporcao in receita.items():
            precisa = proporcao * qtd_montar
            linha_estoque = df_atual[df_atual['CODIGO'] == str(componente)]
            
            if linha_estoque.empty:
                erros.append(f"❌ Componente {componente} não encontrado no cadastro!")
                pode_prosseguir = False
            else:
                saldo = linha_estoque['ESTOQUE'].values[0]
                if saldo < precisa:
                    erros.append(f"⚠️ {componente}: Precisa de {precisa:.2f}, mas o saldo é {saldo:.2f}")
                    pode_prosseguir = False

        if not pode_prosseguir:
            for e in erros: st.error(e)
        else:
            # B. CÁLCULO MATEMÁTICO
            try:
                # 1. Baixa os componentes (insumos)
                for componente, proporcao in receita.items():
                    df_atual.loc[df_atual['CODIGO'] == str(componente), 'ESTOQUE'] -= (proporcao * qtd_montar)
                
                # 2. Adiciona o produto acabado (kit)
                df_atual.loc[df_atual['CODIGO'] == str(id_final), 'ESTOQUE'] += qtd_montar
                
                # C. GRAVAÇÃO NO GOOGLE SHEETS
                conn.update(worksheet="Produtos", data=df_atual)
                
                st.success(f"✅ Montagem do kit {label_escolhido} finalizada!")
                st.balloons()
                st.rerun()
                
            except Exception as ex:
                st.error(f"Erro ao processar montagem: {ex}")

# Rodapé da Sidebar
st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)