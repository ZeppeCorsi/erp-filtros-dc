import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado!")
    st.stop()

st.set_page_config(page_title="Fornecedores | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# ID da Planilha
ID_P = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_F = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Fornecedores"

@st.cache_data(ttl=2)
def carregar_fornecedores():
    try:
        df = pd.read_csv(URL_F)
        df.columns = [str(c).replace('"', '').strip().upper() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

df_forn = carregar_fornecedores()

st.title("🏭 Gestão de Fornecedores")

# --- FORMULÁRIO DE CADASTRO ATUALIZADO ---
with st.expander("➕ Cadastrar Novo Fornecedor"):
    with st.form("form_fornecedor"):
        c1, c2 = st.columns(2)
        nome_red = c1.text_input("Nome Reduzido (Como aparece na lista)").upper()
        razao = c2.text_input("Razão Social completa").upper()
        
        c3, c4, c5 = st.columns([1, 1, 1])
        cnpj = c3.text_input("CNPJ")
        tel = c4.text_input("Telefone")
        vendedor = c5.text_input("Nome do Vendedor/Contato").upper()
        
        cat = st.selectbox("Categoria", ["FILTROS", "REFIS", "CONEXÕES/PEÇAS", "QUARTZO", "CARVÃO", "OUTROS"])
        
        # NOVA COLUNA: Detalhes do Fornecedor
        detalhes_forn = st.text_area("Detalhes Importantes (Prazos, Frete, Acordos)").upper()
        
        if st.form_submit_button("💾 SALVAR FORNECEDOR"):
            if nome_red:
                try:
                    df_atual = conn.read(worksheet="Fornecedores", ttl=0)
                    novo = pd.DataFrame([{
                        "NOME REDUZIDO": nome_red,
                        "RAZÃO SOCIAL": razao,
                        "CNPJ": cnpj,
                        "TELEFONE": tel,
                        "VENDEDOR": vendedor,
                        "CATEGORIA": cat,
                        "DETALHES": detalhes_forn  # Gravando a nova informação
                    }])
                    df_final = pd.concat([df_atual, novo], ignore_index=True)
                    conn.update(worksheet="Fornecedores", data=df_final)
                    st.success(f"Fornecedor {nome_red} cadastrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}. Verifique se a coluna 'DETALHES' existe na aba.")
            else:
                st.warning("O campo 'Nome Reduzido' é obrigatório.")

st.divider()

# --- LISTA E BUSCA ---
st.subheader("🔍 Consultar Fornecedores")
busca = st.text_input("Buscar por Nome ou Categoria")

if not df_forn.empty:
    # Filtro de busca
    df_filtrado = df_forn[
        df_forn['NOME REDUZIDO'].str.contains(busca.upper(), na=False) | 
        df_forn['CATEGORIA'].str.contains(busca.upper(), na=False)
    ]
    
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum fornecedor cadastrado.")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)