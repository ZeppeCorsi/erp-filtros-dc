import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO E SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado!")
    st.stop()

conn = st.connection("gsheets", type=GSheetsConnection)

# ID e URL da Planilha (Certifique-se que o nome da variável é exatamente URL_FORN)
ID_P = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_FORN = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Fornecedores"

@st.cache_data(ttl=2)
def carregar_fornecedores():
    try:
        # Aqui deve ser exatamente URL_FORN
        df = pd.read_csv(URL_FORN)
        df.columns = [c.replace('"', '').strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar fornecedores: {e}")
        return pd.DataFrame()

# --- DIÁLOGO DE EDIÇÃO (POPUP) ---
@st.dialog("🏭 Ficha do Fornecedor")
def editar_fornecedor_dialog(indice, dados):
    st.markdown(f"### Fornecedor: {dados['NOME REDUZIDO']}")
    
    # --- DADOS FIXOS ---
    c1, c2 = st.columns(2)
    c1.text_input("RAZÃO SOCIAL", value=dados.get('RAZÃO SOCIAL', ''), disabled=True)
    c2.text_input("CNPJ", value=dados.get('CNPJ', ''), disabled=True)
    
    # --- DADOS EDITÁVEIS ---
    c3, c4 = st.columns(2)
    novo_nome_red = c3.text_input("NOME REDUZIDO", value=dados.get('NOME REDUZIDO', ''))
    novo_vendedor = c4.text_input("VENDEDOR / CONTATO", value=dados.get('VENDEDOR', ''))
    
    c5, c6 = st.columns(2)
    novo_tel = c5.text_input("TELEFONE", value=dados.get('TELEFONE', ''))
    
    # Lista de categorias atualizada
    categorias = ["FILTROS", "REFIS", "QUARTZO", "CARVÃO", "CONEXÕES/PEÇAS", "OUTROS"]
    cat_atual = dados.get('CATEGORIA', 'OUTROS')
    idx_cat = categorias.index(cat_atual) if cat_atual in categorias else 0
    
    nova_cat = c6.selectbox("CATEGORIA", categorias, index=idx_cat)
    
    # --- DETALHES ---
    st.divider()
    detalhes_antigos = str(dados.get('DETALHES', '')) if str(dados.get('DETALHES', '')) != 'nan' else ""
    novos_detalhes = st.text_area("Notas e Acordos", value=detalhes_antigos, height=150)

    if st.button("💾 ATUALIZAR FORNECEDOR", use_container_width=True):
        try:
            df_full = conn.read(worksheet="Fornecedores", ttl=0)
            
            df_full.at[indice, 'NOME REDUZIDO'] = novo_nome_red.upper()
            df_full.at[indice, 'VENDEDOR'] = novo_vendedor.upper()
            df_full.at[indice, 'TELEFONE'] = novo_tel
            df_full.at[indice, 'CATEGORIA'] = nova_cat
            df_full.at[indice, 'DETALHES'] = novos_detalhes.upper()
            
            conn.update(worksheet="Fornecedores", data=df_full)
            st.success("Dados atualizados!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

# --- INTERFACE PRINCIPAL ---
st.title("🏭 Gestão de Fornecedores - Filtros DC")

aba1, aba2 = st.tabs(["📋 Lista de Fornecedores", "➕ Novo Cadastro"])
df_forn = carregar_fornecedores()

# --- ABA 1: LISTA ---
with aba1:
    if not df_forn.empty:
        busca = st.text_input("🔍 Buscar fornecedor...")
        
        if busca:
            mask = df_forn.apply(lambda r: r.astype(str).str.contains(busca, case=False).any(), axis=1)
            df_exibir = df_forn[mask]
        else:
            df_exibir = df_forn

        st.divider()
        h1, h2, h3, h4, h5 = st.columns([2, 2, 2, 2, 1])
        h1.markdown("**FORNECEDOR**")
        h2.markdown("**CATEGORIA**")
        h3.markdown("**VENDEDOR**")
        h4.markdown("**CONTATO**")
        h5.markdown("**AÇÃO**")
        st.divider()

        for i, row in df_exibir.iterrows():
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
            c1.write(f"**{row.get('NOME REDUZIDO', '')}**")
            c2.write(row.get('CATEGORIA', ''))
            c3.write(row.get('VENDEDOR', ''))
            c4.write(row.get('TELEFONE', ''))
            
            if c5.button("✏️ Ver/Edit", key=f"forn_{i}"):
                editar_fornecedor_dialog(i, row)
            st.divider()
    else:
        st.info("Nenhum fornecedor cadastrado.")

# --- ABA 2: NOVO CADASTRO ---
with aba2:
    with st.form("form_novo_fornecedor", clear_on_submit=True):
        st.subheader("Cadastro de Novo Fornecedor")
        col1, col2 = st.columns(2)
        f_nome_red = col1.text_input("NOME REDUZIDO (Fantasia) *")
        f_razao = col2.text_input("RAZÃO SOCIAL *")
        
        col3, col4, col5 = st.columns([1.5, 1.5, 2])
        f_cnpj = col3.text_input("CNPJ")
        f_tel = col4.text_input("TELEFONE")
        f_vendedor = col5.text_input("VENDEDOR")
        
        f_cat = st.selectbox("CATEGORIA", ["FILTROS", "REFIS", "QUARTZO", "CARVÃO", "CONEXÕES/PEÇAS", "OUTROS"])
        f_detalhes = st.text_area("DETALHES / NOTAS")
        
        if st.form_submit_button("✅ SALVAR FORNECEDOR", use_container_width=True):
            if not f_nome_red or not f_razao:
                st.error("Campos obrigatórios faltando!")
            else:
                try:
                    df_novo = pd.DataFrame([{
                        "NOME REDUZIDO": f_nome_red.upper(),
                        "RAZÃO SOCIAL": f_razao.upper(),
                        "CNPJ": f_cnpj,
                        "TELEFONE": f_tel,
                        "VENDEDOR": f_vendedor.upper(),
                        "CATEGORIA": f_cat,
                        "DETALHES": f_detalhes.upper()
                    }])
                    df_final = pd.concat([df_forn, df_novo], ignore_index=True)
                    conn.update(worksheet="Fornecedores", data=df_final)
                    st.success("Salvo com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)