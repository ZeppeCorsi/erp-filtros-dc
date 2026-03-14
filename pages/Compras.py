import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. SEGURANÇA E CONEXÃO
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

st.set_page_config(page_title="Compras | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Inicialização da Cesta de Compras
if 'cesta_compras' not in st.session_state: st.session_state.cesta_compras = []

ID_P = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_P = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Produtos"
URL_F = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Fornecedores"

@st.cache_data(ttl=2)
def carregar_dados():
    try:
        p = pd.read_csv(URL_P)
        f = pd.read_csv(URL_F)
        p.columns = [str(c).strip().upper() for c in p.columns]
        f.columns = [str(c).strip().upper() for c in f.columns]
        return p, f
    except:
        return pd.DataFrame(), pd.DataFrame()

df_produtos, df_fornecedores = carregar_dados()

st.title("📦 Lançamento de Compras (Entrada)")

# --- 1. FORNECEDOR ---
with st.container(border=True):
    col_f1, col_f2 = st.columns([3, 1])
    if not df_fornecedores.empty:
        col_nome_forn = next((c for c in df_fornecedores.columns if 'NOME' in c or 'RAZAO' in c), df_fornecedores.columns[0])
        lista_forn = sorted(df_fornecedores[col_nome_forn].astype(str).unique().tolist())
        fornecedor_sel = col_f1.selectbox("Selecione o Fornecedor", [""] + lista_forn)
    else:
        fornecedor_sel = col_f1.text_input("Nome do Fornecedor (Planilha vazia)")
    
    data_compra = col_f2.date_input("Data da Compra", datetime.now())

# --- 2. ADICIONAR ITENS ---
st.subheader("🛒 Itens da Nota/Pedido")
with st.container(border=True):
    c1, c2, c3 = st.columns([3, 1, 1])
    
    # Campo de busca/seleção com opção de digitar novo
    lista_prod_estoque = df_produtos['NOME'].unique().tolist() if 'NOME' in df_produtos.columns else []
    item_nome = c1.selectbox("Produto no Estoque", ["+ CADASTRAR NOVO ITEM"] + lista_prod_estoque)
    
    if item_nome == "+ CADASTRAR NOVO ITEM":
        novo_item_nome = st.text_input("Digite o nome do novo produto:").upper()
        item_para_cesta = novo_item_nome
    else:
        item_para_cesta = item_nome

    qtd_compra = c2.number_input("QTD Comprada", min_value=1, value=1)
    preco_custo = c3.number_input("Custo Unitário (R$)", min_value=0.0, format="%.2f")

    if st.button("➕ ADICIONAR À COMPRA", use_container_width=True):
        if item_para_cesta:
            st.session_state.cesta_compras.append({
                "ITEM": item_para_cesta,
                "QTD": qtd_compra,
                "UNIT": preco_custo,
                "TOTAL": qtd_compra * preco_custo,
                "NOVO": (item_nome == "+ CADASTRAR NOVO ITEM")
            })
            st.rerun()

# --- 3. RESUMO E PARCELAMENTO ---
if st.session_state.cesta_compras:
    st.write("### 📝 Resumo da Compra")
    total_compra = 0.0
    for i, it in enumerate(st.session_state.cesta_compras):
        with st.container(border=True):
            col_r1, col_r2 = st.columns([4, 1])
            tag_novo = " (🆕 NOVO)" if it["NOVO"] else ""
            col_r1.write(f"**{it['ITEM']}**{tag_novo}")
            col_r1.caption(f"{it['QTD']} un x R$ {it['UNIT']:,.2f} = R$ {it['TOTAL']:,.2f}")
            if col_r2.button("🗑️", key=f"del_{i}"):
                st.session_state.cesta_compras.pop(i)
                st.rerun()
            total_compra += it["TOTAL"]

    st.info(f"#### 💰 TOTAL DA COMPRA: R$ {total_compra:,.2f}")

    # --- PARCELAMENTO PROGRAMÁVEL (SAÍDA) ---
    st.divider()
    st.subheader("🏦 Programação de Pagamento (Saída)")
    with st.container(border=True):
        col_p1, col_p2 = st.columns(2)
        n_parcelas = col_p1.number_input("Parcelar em:", min_value=1, max_value=6, value=1)
        status_pgto = col_p2.selectbox("Status", ["PENDENTE", "PAGO"])
        
        dados_saida = []
        soma_saida = 0.0
        cols_datas = st.columns(3)
        for i in range(int(n_parcelas)):
            c_dt = cols_datas[i % 3]
            dt_venc = c_dt.date_input(f"Venc. {i+1}/{n_parcelas}", datetime.now(), key=f"venc_{i}")
            sugestao_v = total_compra if i == 0 else 0.0
            val_v = c_dt.number_input(f"Valor R$ ({i+1})", min_value=0.0, value=float(sugestao_v), key=f"val_s_{i}")
            dados_saida.append({"DATA": dt_venc, "VALOR": val_v, "PARC": f"{i+1}/{n_parcelas}"})
            soma_saida += val_v

        restante = round(total_compra - soma_saida, 2)
        if restante == 0: st.success("✅ Valores conferem!")
        else: st.warning(f"⚠️ Diferença: R$ {restante:,.2f}")

    # --- 4. FINALIZAR COMPRA ---
    if st.button("🚀 FINALIZAR COMPRA E ATUALIZAR TUDO", use_container_width=True, type="primary", disabled=(restante != 0)):
        try:
            # A. ATUALIZAR ESTOQUE (E CRIAR NOVOS ITENS)
            df_est = conn.read(worksheet="Produtos", ttl=0)
            df_est.columns = [str(c).strip().upper() for c in df_est.columns]
            
            for it in st.session_state.cesta_compras:
                mask = df_est['NOME'] == it["ITEM"]
                if mask.any():
                    # Soma ao estoque existente
                    df_est.loc[mask, 'ESTOQUE'] = pd.to_numeric(df_est.loc[mask, 'ESTOQUE']).fillna(0) + it["QTD"]
                    # Atualiza o preço de custo se desejar
                    df_est.loc[mask, 'PRECO_CUSTO'] = it["UNIT"]
                else:
                    # Cria novo item se não existir
                    novo_prod = pd.DataFrame([{"NOME": it["ITEM"], "ESTOQUE": it["QTD"], "PRECO_CUSTO": it["UNIT"]}])
                    df_est = pd.concat([df_est, novo_prod], ignore_index=True)
            
            conn.update(worksheet="Produtos", data=df_est)

            # B. LANÇAR SAÍDAS NO FLUXO DE CAIXA
            df_caixa = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
            lancamentos_saida = []
            for s in dados_saida:
                lancamentos_saida.append({
                    "DATA": s["DATA"].strftime("%d/%m/%Y"),
                    "TIPO": "SAIDA",
                    "DESCRICAO": f"COMPRA - {fornecedor_sel}".upper(),
                    "VALOR": s["VALOR"],
                    "PARCELA": s["PARC"],
                    "STATUS": status_pgto.replace("PAGO", "RECEBIDO"), # Mantendo o padrão da sua coluna Status
                    "CLIENTE": fornecedor_sel # Aqui o 'cliente' é o fornecedor
                })
            df_caixa_f = pd.concat([df_caixa, pd.DataFrame(lancamentos_saida)], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_caixa_f)

            st.success("🎉 Compra registrada! Estoque e Caixa atualizados.")
            st.session_state.cesta_compras = []
            st.balloons()
            st.rerun()

        except Exception as e:
            st.error(f"Erro no processamento: {e}")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)