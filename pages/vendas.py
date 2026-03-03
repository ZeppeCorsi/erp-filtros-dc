import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

st.set_page_config(page_title="Vendas | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Inicialização da Cesta
if 'cesta' not in st.session_state: st.session_state.cesta = []
if 'idx_c' not in st.session_state: st.session_state.idx_c = 0

ID_P = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_C = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Clientes"
URL_P = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Produtos"

def limpar_colunas(df):
    df.columns = [str(c).replace('"', '').strip().upper() for c in df.columns]
    return df

@st.cache_data(ttl=2)
def carregar():
    try:
        c = pd.read_csv(URL_C)
        p = pd.read_csv(URL_P)
        return limpar_colunas(c), limpar_colunas(p)
    except Exception as e:
        st.error(f"Erro ao ler planilha: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_clientes, df_produtos = carregar()

st.title("🛒 Lançamento de Venda")

# --- 1. IDENTIFICAÇÃO ---
st.subheader("1. Cliente")
c_b, c_l = st.columns([3, 1])
busca = c_b.text_input("Buscar cliente por nome", placeholder="Digite parte do nome...")

col_nome_cli = 'NOME REDUZIDO' if 'NOME REDUZIDO' in df_clientes.columns else next((c for c in df_clientes.columns if 'NOME' in c), None)

if col_nome_cli and not df_clientes.empty:
    lista_nomes = df_clientes[col_nome_cli].astype(str).dropna().sort_values().unique().tolist()
    
    if c_l.button("🔍 Buscar"):
        match = [n for n in lista_nomes if busca.upper() in str(n).upper()]
        if match: 
            st.session_state.idx_c = lista_nomes.index(match[0])
            st.rerun()
        else: st.warning("Não encontrado.")

    col1, col2 = st.columns([3, 1])
    cliente_final = col1.selectbox("Confirme o Cliente", options=lista_nomes, index=st.session_state.idx_c if st.session_state.idx_c < len(lista_nomes) else 0)
    data_op = col2.date_input("Data", datetime.now(), format="DD/MM/YYYY")
else:
    st.error("Coluna de Nome não encontrada na aba Clientes.")
    st.stop()

st.divider()

# --- 2. ITENS ---
st.subheader("2. Produtos")
col_prod = "NOME" if "NOME" in df_produtos.columns else next((c for c in df_produtos.columns if 'DESCRI' in c or 'PRODUTO' in c), None)
col_preco = "PRECO" if "PRECO" in df_produtos.columns else next((c for c in df_produtos.columns if 'LISTA' in c or 'VALOR' in c), None)

if col_prod and col_preco:
    with st.container(border=True):
        c3, c4, c5 = st.columns([2, 1, 1])
        lista_itens_prod = df_produtos[col_prod].astype(str).unique().tolist()
        prod_sel = c3.selectbox("Selecione o Item", options=lista_itens_prod)
        
        linha_p = df_produtos[df_produtos[col_prod] == prod_sel]
        p_bruto = linha_p[col_preco].values[0] if not linha_p.empty else 0.0
        if isinstance(p_bruto, str): p_bruto = p_bruto.replace('.', '').replace(',', '.')
        try: preco_unit = float(p_bruto)
        except: preco_unit = 0.0

        qtd = c4.number_input("QTD", min_value=1, value=1)
        valor_u = c5.number_input("Preço Unit (R$)", min_value=0.0, value=preco_unit, format="%.2f")
        
        if st.button("➕ ADICIONAR ITEM", use_container_width=True):
            st.session_state.cesta.append({
                "ITEM": prod_sel, "QTD": qtd, "UNIT": valor_u, "TOTAL": qtd * valor_u
            })
            st.rerun()

# --- 3. RESUMO E FECHAMENTO ---
if st.session_state.cesta:
    st.write("### 📝 Itens do Pedido")
    for i, item in enumerate(st.session_state.cesta):
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            cols[0].write(f"**{i+1}. {item['ITEM']}**")
            cols[0].write(f"R$ {item['UNIT']:,.2f} x {item['QTD']} = **R$ {item['TOTAL']:,.2f}**")
            if cols[1].button("➖", key=f"m_{i}"):
                if item['QTD'] > 1:
                    st.session_state.cesta[i]['QTD'] -= 1
                    st.session_state.cesta[i]['TOTAL'] = st.session_state.cesta[i]['QTD'] * item['UNIT']
                else: st.session_state.cesta.pop(i)
                st.rerun()
            if cols[2].button("➕", key=f"p_{i}"):
                st.session_state.cesta[i]['QTD'] += 1
                st.session_state.cesta[i]['TOTAL'] = st.session_state.cesta[i]['QTD'] * item['UNIT']
                st.rerun()
            if cols[3].button("🗑️", key=f"d_{i}"):
                st.session_state.cesta.pop(i)
                st.rerun()

    total_geral = sum(it['TOTAL'] for it in st.session_state.cesta)
    st.info(f"#### 💰 TOTAL GERAL: R$ {total_geral:,.2f}")
    
    # --- NOVOS CAMPOS DE FECHAMENTO ---
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        forma_pagto = st.selectbox(
            "💳 Forma de Pagamento:",
            options=["A VISTA", "30 DIAS", "2 VEZES", "3 VEZES"]
        )
    with col_f2:
        obs = st.text_area("Observações").upper()

    if st.button("🚀 FINALIZAR E SALVAR", use_container_width=True, type="primary"):
        try:
            vendedor_atual = st.session_state.get('usuario', 'SISTEMA')
            df_vendas_db = conn.read(worksheet="Vendas", ttl=0)
            
            novas = []
            for it in st.session_state.cesta:
                novas.append({
                    "DATA": data_op.strftime("%d/%m/%Y"),
                    "CLIENTE": cliente_final,
                    "PRODUTO": it["ITEM"],
                    "QTD": it["QTD"],
                    "VALOR UNIT": it["UNIT"],
                    "TOTAL": it["TOTAL"],
                    "VENDEDOR": vendedor_atual,
                    "FORMA DE PAGAMENTO": forma_pagto, # Coluna solicitada
                    "OBS": obs
                })
            
            df_final = pd.concat([df_vendas_db, pd.DataFrame(novas)], ignore_index=True)
            conn.update(worksheet="Vendas", data=df_final)
            
            st.session_state.venda_finalizada = True
            st.success(f"✅ Venda ({forma_pagto}) registrada com sucesso!")
            
        except Exception as e:
            st.error(f"Erro ao salvar venda: {e}")

    # --- PERGUNTA DE BAIXA DE ESTOQUE ---
    if st.session_state.get('venda_finalizada'):
        with st.container(border=True):
            st.warning("❓ **Deseja abater os itens vendidos do Estoque agora?**")
            col_sim, col_nao = st.columns(2)
            
            if col_sim.button("✅ SIM, BAIXAR ESTOQUE", use_container_width=True):
                try:
                    df_prod_estoque = conn.read(worksheet="Produtos", ttl=0)
                    df_prod_estoque.columns = [str(c).strip().upper() for c in df_prod_estoque.columns]
                    
                    for it in st.session_state.cesta:
                        mask = df_prod_estoque['NOME'] == it["ITEM"]
                        if mask.any():
                            df_prod_estoque.loc[mask, 'ESTOQUE'] = pd.to_numeric(df_prod_estoque.loc[mask, 'ESTOQUE']).fillna(0) - it["QTD"]
                    
                    conn.update(worksheet="Produtos", data=df_prod_estoque)
                    st.success("📦 Estoque atualizado!")
                    st.balloons()
                    st.session_state.cesta = []
                    st.session_state.venda_finalizada = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro no estoque: {e}")

            if col_nao.button("❌ NÃO, APENAS FINALIZAR", use_container_width=True):
                st.session_state.cesta = []
                st.session_state.venda_finalizada = False
                st.rerun()

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)