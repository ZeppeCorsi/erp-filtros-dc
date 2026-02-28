import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

st.set_page_config(page_title="Orçamentos | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Inicialização da Cesta de Orçamento
if 'cesta_orc' not in st.session_state: st.session_state.cesta_orc = []
if 'idx_o' not in st.session_state: st.session_state.idx_o = 0

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

df_cli, df_prod = carregar()

st.title("📄 Novo Orçamento")

# --- 1. CLIENTE ---
st.subheader("1. Identificação do Cliente")
c_b, c_l = st.columns([3, 1])
busca = c_b.text_input("Buscar cliente por nome", placeholder="Ex: HOTEL")

col_nome_cli = next((c for c in df_cli.columns if 'NOME' in c), None)

if col_nome_cli and not df_cli.empty:
    lista_nomes = df_cli[col_nome_cli].dropna().sort_values().tolist()
    
    if c_l.button("🔍 Buscar"):
        match = [n for n in lista_nomes if busca.upper() in str(n).upper()]
        if match: st.session_state.idx_o = lista_nomes.index(match[0])
        else: st.warning("Não encontrado.")

    col1, col2 = st.columns([3, 1])
    cliente_orc = col1.selectbox("Confirme o Cliente", options=lista_nomes, index=st.session_state.idx_o)
    validade_orc = col2.date_input("Válido até", datetime.now(), format="DD/MM/YYYY")
else:
    st.error("Dados de clientes não carregados.")
    st.stop()

st.divider()

# --- 2. PRODUTOS COM DETALHES ---
st.subheader("2. Itens do Orçamento")
col_prod = next((c for c in df_prod.columns if 'DESCRI' in c or 'PRODUTO' in c), None)
col_preco = next((c for c in df_prod.columns if 'LISTA' in c or 'VALOR' in c), None)

if col_prod and col_preco:
    with st.container(border=True):
        c3, c4, c5 = st.columns([2, 1, 1])
        prod_sel = c3.selectbox("Produto", options=df_prod[col_prod].unique())
        
        p_bruto = df_prod[df_prod[col_prod] == prod_sel][col_preco].values[0]
        if isinstance(p_bruto, str): p_bruto = p_bruto.replace('.', '').replace(',', '.')
        preco_unit = float(p_bruto) if p_bruto else 0.0

        qtd = c4.number_input("QTD", min_value=1, value=1)
        valor_u = c5.number_input("Preço Unit (R$)", min_value=0.0, value=preco_unit, format="%.2f")
        
        # ESPAÇO 1: DETALHES ESPECÍFICOS DO ITEM
        detalhes_item = st.text_area("🔧 Detalhes Técnicos deste Item", placeholder="Ex: Material, medidas, conexões específicas...")

        if st.button("➕ ADICIONAR AO ORÇAMENTO", use_container_width=True):
            st.session_state.cesta_orc.append({
                "ITEM": prod_sel,
                "DETALHES": detalhes_item.upper(),
                "QTD": qtd,
                "UNIT": valor_u,
                "TOTAL": qtd * valor_u
            })
            st.rerun()

# --- 3. RESUMO E GRAVAÇÃO ---
if st.session_state.cesta_orc:
    st.write("### 📝 Resumo da Proposta")
    for i, item in enumerate(st.session_state.cesta_orc):
        with st.container(border=True):
            cols = st.columns([4, 1, 1, 1])
            cols[0].write(f"**{i+1}. {item['ITEM']}**")
            if item['DETALHES']:
                cols[0].caption(f"Especificações: {item['DETALHES']}")
            cols[0].write(f"R$ {item['UNIT']:,.2f} x {item['QTD']} = **R$ {item['TOTAL']:,.2f}**")
            
            # Botões + e - para ajuste rápido
            if cols[1].button("➖", key=f"mo_{i}"):
                if item['QTD'] > 1:
                    st.session_state.cesta_orc[i]['QTD'] -= 1
                    st.session_state.cesta_orc[i]['TOTAL'] = st.session_state.cesta_orc[i]['QTD'] * item['UNIT']
                else: st.session_state.cesta_orc.pop(i)
                st.rerun()
            if cols[2].button("➕", key=f"po_{i}"):
                st.session_state.cesta_orc[i]['QTD'] += 1
                st.session_state.cesta_orc[i]['TOTAL'] = st.session_state.cesta_orc[i]['QTD'] * item['UNIT']
                st.rerun()
            if cols[3].button("🗑️", key=f"do_{i}"):
                st.session_state.cesta_orc.pop(i)
                st.rerun()

    total_geral = sum(it['TOTAL'] for it in st.session_state.cesta_orc)
    st.info(f"#### 💰 VALOR TOTAL: R$ {total_geral:,.2f}")
    
    # ESPAÇO 2: CONDIÇÕES GERAIS DO ORÇAMENTO
    obs_gerais = st.text_area("📝 Condições Gerais (Pagamento, Prazo de Entrega, Frete)", 
                             "PAGAMENTO: 30 DIAS | ENTREGA: 05 DIAS ÚTEIS | FRETE: FOB").upper()

    # ... (mantenha o restante do código igual até o botão de salvar)

if st.button("💾 SALVAR ORÇAMENTO NA PLANILHA", use_container_width=True, type="primary"):
        try:
            # 1. Lê a planilha - Forçamos a limpeza de dados vazios
            df_atual = conn.read(worksheet="Orcamentos", ttl=0).dropna(how='all')
            
            novas_linhas = []
            for it in st.session_state.cesta_orc:
                novas_linhas.append({
                    "DATA": datetime.now().strftime("%d/%m/%Y"),
                    "VALIDADE": validade_orc.strftime("%d/%m/%Y"),
                    "CLIENTE": cliente_orc,
                    "PRODUTO": it["ITEM"],
                    "QT": it["QTD"],
                    "VALOR UNITARIO": it["UNIT"],
                    "VALOR TOTAL": it["TOTAL"],
                    "VENDEDOR": st.session_state.usuario_atual,
                    "CONDICOES GERAIS": obs_gerais,
                    "DETALHES": it["DETALHES"]
                })
            
            df_novos = pd.DataFrame(novas_linhas)
            
            # 2. Unimos apenas as colunas que você tem na planilha (A até J)
            df_final = pd.concat([df_atual, df_novos], ignore_index=True)
            
            # 3. Gravação direta na aba
            conn.update(worksheet="Orcamentos", data=df_final)
            
            st.success("✅ ORÇAMENTO SALVO!")
            st.session_state.cesta_orc = []
            st.balloons()
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro técnico: {e}")