import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

st.set_page_config(page_title="Estoque | Filtros DC", layout="wide")

# 2. CONFIGURAÇÃO DE CONEXÃO
ID_PLANILHA = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
# Usando o nome da aba como 'Produtos' (verifique se é este o nome na sua planilha)
URL_PRODUTOS = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/gviz/tq?tqx=out:csv&sheet=Produtos"
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_estoque():
    try:
        df = pd.read_csv(URL_PRODUTOS)
        df.columns = [c.replace('"', '').strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- INTERFACE ---
st.title("📦 Controle de Estoque - Filtros DC")

aba1, aba2 = st.tabs(["📋 Saldo em Estoque", "➕ Cadastrar Novo Item"])

df_estoque = carregar_estoque()

with aba1:
    if not df_estoque.empty:
        # Filtro de busca rápida
        busca = st.text_input("🔍 Buscar produto por nome ou código...")
        
        if busca:
            df_filtrado = df_estoque[df_estoque.apply(lambda r: r.astype(str).str.contains(busca, case=False).any(), axis=1)]
        else:
            df_filtrado = df_estoque
            
        # 1. Pegar o perfil que foi definido no login (home.py)
        # Note que usamos 'perfil' em minúsculo porque o Streamlit costuma padronizar
        # Mas para garantir, vamos testar se ele existe
        perfil_usuario = st.session_state.get('perfil', 'VISITANTE').upper().strip()

        # 2. Lista de colunas que só o ADM vê
        colunas_privadas = ["Custo total", "Markup"]

        # 3. Lógica de decisão
        if perfil_usuario == "ADM":
            df_exibicao = df_estoque
            st.success(f"🔓 Modo Administrador: Exibindo custos e markup.")
        else:
            # Se não for ADM, remove as colunas sensíveis
            df_exibicao = df_estoque.drop(columns=[c for c in colunas_privadas if c in df_estoque.columns])
            st.info("ℹ️ Modo Vendedor: Informações de custo ocultas.")

        # 4. Exibição da Tabela
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        

        # # Exibição com destaque para quantidade
        # st.dataframe(
        #     df_filtrado, 
        #     use_container_width=True, 
        #     hide_index=True,
        #     column_config={
        #         "PRECO": st.column_config.NumberColumn("Preço Venda", format="R$ %.2f"),
        #         "ESTOQUE": st.column_config.NumberColumn("Qtd. Atual")
        #     }
        # )
        
        # Resumo rápido no rodapé da tabela
        total_itens = len(df_filtrado)
        st.caption(f"Exibindo {total_itens} itens no inventário.")
    else:
        st.warning("Nenhum produto encontrado na aba 'Produtos'.")

with aba2:
    st.subheader("Entrada de Novo Produto")
    
    # Lógica de ID Automático (NR PRODUTO)
    proximo_id = 1
    if not df_estoque.empty:
        col_id = df_estoque.columns[0] # Assume que a primeira coluna é o ID
        ultimo_id = pd.to_numeric(df_estoque[col_id], errors='coerce').max()
        if not pd.isna(ultimo_id):
            proximo_id = int(ultimo_id + 1)

    with st.form("form_produto", clear_on_submit=True):
        st.info(f"🔢 Código do novo item: **{proximo_id}**")

        col_nome, col_cat = st.columns([2, 1])
        nome_produto = col_nome.text_input("Nome Curto (Ex: FC500) *")
                
        col1, col2 = st.columns([3, 1])
        descricao = col1.text_input("Descrição do Produto (Ex: Filtro Cartucho 10') *")
        unidade = col2.selectbox("Unidade", ["UN", "PC", "KG", "MT", "CJ"])
        
        col3, col4, col5 = st.columns(3)
        estoque_inicial = col3.number_input("Quantidade Inicial em Estoque", min_value=0, value=0)
        preco_venda = col4.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
        categoria = col5.text_input("Categoria / Grupo")

        if st.form_submit_button("✅ Cadastrar no Estoque"):
            if descricao:
                try:
                    df_base = conn.read(worksheet="Produtos", ttl=0)
                    
                    # Monta a nova linha (ajuste os nomes das colunas se necessário)
                    novo_item = pd.DataFrame([{
                        "CODIGO": proximo_id,
                        "NOME": descricao.upper(), # Pode ser ajustado para receber um nome separado se necessário  
                        "DESCRICAO": descricao.upper(),
                        "UN": unidade,
                        "ESTOQUE": estoque_inicial,
                        "PRECO": preco_venda,
                        "PESO": 0, # Pode ser ajustado para receber peso se necessário
                        "CATEGORIA": categoria.upper()
                    }])
                    
                    df_final = pd.concat([df_base, novo_item], ignore_index=True)
                    conn.update(worksheet="Produtos", data=df_final)
                    
                    st.success(f"Produto {descricao} cadastrado com sucesso!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.error("A descrição do produto é obrigatória.")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)