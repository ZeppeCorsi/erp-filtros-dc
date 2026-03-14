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

ID_P = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_P = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Produtos"

def limpar_colunas(df):
    df.columns = [str(c).replace('"', '').strip().upper() for c in df.columns]
    return df

@st.cache_data(ttl=2)
def carregar_bases():
    try:
        p = pd.read_csv(URL_P)
        return limpar_colunas(p)
    except:
        return pd.DataFrame()

df_produtos = carregar_bases()

st.title("🛒 Efetivar Venda de Orçamento")

# --- 1. BUSCA DE ORÇAMENTO (SUBSTITUINDO BUSCA DE CLIENTE) ---
st.subheader("1. Selecione o Orçamento Aprovado")
with st.container(border=True):
    # Lemos a base de orçamentos
    df_orc = conn.read(worksheet="Orcamentos", ttl=0).dropna(how='all')
    
    if not df_orc.empty:
        # Criamos a lista de opções: "DATA - CLIENTE"
        df_orc['OPCAO'] = df_orc['DATA'].astype(str) + " - " + df_orc['CLIENTE'].astype(str)
        lista_disponivel = sorted(df_orc['OPCAO'].unique().tolist(), reverse=True)
        
        orc_selecionado = st.selectbox("Escolha o orçamento para efetivar:", [""] + lista_disponivel)
        
        if orc_selecionado != "":
            if st.button("📂 IMPORTAR ITENS DO ORÇAMENTO", use_container_width=True):
                data_o, cli_o = orc_selecionado.split(" - ", 1)
                
                # Filtramos os itens desse orçamento
                itens_importados = df_orc[(df_orc['DATA'] == data_o) & (df_orc['CLIENTE'] == cli_o)]
                
                # Preenchemos os dados do cliente e a cesta na session_state
                st.session_state.cliente_venda = cli_o
                st.session_state.cesta = []
                for _, linha in itens_importados.iterrows():
                    st.session_state.cesta.append({
                        "ITEM": linha["PRODUTO"],
                        "QTD": int(linha["QT"]),
                        "UNIT": float(linha["VALOR UNITARIO"]),
                        "TOTAL": float(linha["VALOR TOTAL"])
                    })
                st.success(f"Itens de {cli_o} importados com sucesso!")
                st.rerun()
    else:
        st.warning("Nenhum orçamento encontrado na planilha.")

st.divider()

# --- 2. DADOS DA VENDA CARREGADA ---
# Verificamos se há um cliente selecionado via orçamento
cliente_final = st.session_state.get('cliente_venda', "Nenhum selecionado")

col_v1, col_v2 = st.columns([3, 1])
col_v1.info(f"👤 **Cliente:** {cliente_final}")
data_op = col_v2.date_input("Data da Venda", datetime.now(), format="DD/MM/YYYY")

# --- 3. RESUMO E FECHAMENTO ---
if st.session_state.cesta:
    st.write("### 📝 Itens do Pedido")
    for i, item in enumerate(st.session_state.cesta):
        with st.container(border=True):
            cols = st.columns([4, 1, 1])
            cols[0].write(f"**{i+1}. {item['ITEM']}**")
            cols[0].write(f"R$ {item['UNIT']:,.2f} x {item['QTD']} = **R$ {item['TOTAL']:,.2f}**")
            
            # Botões para ajustes finos na hora da venda
            if cols[1].button("➖", key=f"m_{i}"):
                if item['QTD'] > 1:
                    st.session_state.cesta[i]['QTD'] -= 1
                    st.session_state.cesta[i]['TOTAL'] = st.session_state.cesta[i]['QTD'] * item['UNIT']
                else: st.session_state.cesta.pop(i)
                st.rerun()
            if cols[2].button("🗑️", key=f"d_{i}"):
                st.session_state.cesta.pop(i)
                st.rerun()

    total_geral = sum(it['TOTAL'] for it in st.session_state.cesta)
    st.info(f"#### 💰 TOTAL GERAL DA VENDA: R$ {total_geral:,.2f}")

# --- 4. FATURAMENTO (FLUXO DE CAIXA) ---
if st.session_state.get('venda_finalizada'):
    st.divider()
    with st.container(border=True):
        st.subheader("🏦 Faturamento - Fluxo de Caixa")
        
        col_parc1, col_parc2 = st.columns([1, 2])
        num_parcelas = col_parc1.number_input("Qtd de Parcelas", min_value=1, max_value=12, value=1)
        status_inicial = col_parc2.selectbox("Status Inicial", ["PENDENTE", "RECEBIDO"])

        valor_parcela = round(total_geral / num_parcelas, 2)
        
        st.write("📅 **Defina as datas de vencimento:**")
        lista_datas = []
        cols_datas = st.columns(3) 
        for i in range(num_parcelas):
            com_col = cols_datas[i % 3] 
            data_p = com_col.date_input(f"Data Parcela {i+1}/{num_parcelas}", datetime.now(), key=f"dt_parc_{i}")
            lista_datas.append(data_p)

        if st.button("💰 CONFIRMAR E LANÇAR NO CAIXA", use_container_width=True, type="primary"):
            try:
                # 1. CRIAMOS A LISTA AQUI (Evita o erro 'not defined')
                novas_lancamentos = [] 
                
                # 2. LEMOS A PLANILHA
                df_caixa = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
                
                # 3. ALIMENTAMOS A LISTA
                for i in range(num_parcelas):
                    novas_lancamentos.append({
                        "DATA": lista_datas[i].strftime("%d/%m/%Y"),
                        "TIPO": "ENTRADA",
                        "DESCRICAO": f"VENDA - {cliente_final}".upper(),
                        "VALOR": valor_parcela,
                        "PARCELA": f"{i+1}/{num_parcelas}",
                        "STATUS": status_inicial,
                        "CLIENTE": cliente_final
                    })
                
                # 4. SALVAMOS
                df_final_caixa = pd.concat([df_caixa, pd.DataFrame(novas_lancamentos)], ignore_index=True)
                conn.update(worksheet="Fluxo de Caixa", data=df_final_caixa)
                
                st.success(f"✅ {num_parcelas} lançamentos criados!")
                st.balloons()
                
                # Reset para próxima venda
                st.session_state.cesta = []
                st.session_state.venda_finalizada = False
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao salvar no Fluxo de Caixa: {e}")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        forma_pagto = st.selectbox("💳 Forma de Pagamento:", ["A VISTA", "30 DIAS", "CARTÃO", "PIX"])
    with col_f2:
        obs = st.text_area("Observações da Venda").upper()

    if st.button("🚀 FINALIZAR E SALVAR VENDA", use_container_width=True, type="primary"):
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
                    "FORMA DE PAGAMENTO": forma_pagto,
                    "OBS": obs
                })
            
            df_final = pd.concat([df_vendas_db, pd.DataFrame(novas)], ignore_index=True)
            conn.update(worksheet="Vendas", data=df_final)
            
            st.session_state.venda_finalizada = True
            st.success("✅ Venda registrada!")
            
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    # --- BAIXA DE ESTOQUE ---
    if st.session_state.get('venda_finalizada'):
        with st.container(border=True):
            st.warning("📦 **Deseja abater esses itens do Estoque?**")
            if st.button("✅ SIM, BAIXAR AGORA"):
                df_estoque = conn.read(worksheet="Produtos", ttl=0)
                df_estoque.columns = [str(c).strip().upper() for c in df_estoque.columns]
                for it in st.session_state.cesta:
                    mask = df_estoque['NOME'] == it["ITEM"]
                    if mask.any():
                        df_estoque.loc[mask, 'ESTOQUE'] = pd.to_numeric(df_estoque.loc[mask, 'ESTOQUE']).fillna(0) - it["QTD"]
                conn.update(worksheet="Produtos", data=df_estoque)
                st.session_state.cesta = []
                st.session_state.venda_finalizada = False
                st.session_state.cliente_venda = None
                st.rerun()

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)