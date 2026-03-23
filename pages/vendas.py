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

# --- 1. BUSCA DE ORÇAMENTO ---
st.subheader("1. Selecione o Orçamento Aprovado")
with st.container(border=True):
    df_orc = conn.read(worksheet="Orcamentos", ttl=0).dropna(how='all')
    
    if not df_orc.empty:
        # --- NOVIDADE: Filtramos apenas os ABERTOS ---
        df_orc_abertos = df_orc[df_orc['STATUS'] == "ABERTO"].copy()
        
        if not df_orc_abertos.empty:
            # Criamos a lista com o Número para facilitar a localização exata
            df_orc_abertos['OPCAO'] = "Nº " + df_orc_abertos['NUMERO'].astype(str) + " - " + df_orc_abertos['CLIENTE'].astype(str)
            lista_disponivel = sorted(df_orc_abertos['OPCAO'].unique().tolist(), reverse=True)
            
            orc_selecionado = st.selectbox("Escolha o orçamento para efetivar:", [""] + lista_disponivel)
            
            if orc_selecionado != "":
                if st.button("📂 IMPORTAR ITENS DO ORÇAMENTO", use_container_width=True):
                    # Extraímos o número do orçamento da string
                    num_o = orc_selecionado.split(" - ")[0].replace("Nº ", "")
                    
                    # Filtramos os itens pelo número (mais seguro que data/cliente)
                    itens_importados = df_orc_abertos[df_orc_abertos['NUMERO'].astype(str) == num_o]
                    cli_o = itens_importados.iloc[0]['CLIENTE']
                    
                    # Guardamos o número no session_state para dar baixa depois
                    st.session_state.num_orc_venda = num_o
                    st.session_state.cliente_venda = cli_o
                    st.session_state.cesta = []
                    
                    for _, linha in itens_importados.iterrows():
                        st.session_state.cesta.append({
                            "ITEM": linha["PRODUTO"],
                            "QTD": int(linha["QT"]),
                            "UNIT": float(linha["VALOR UNITARIO"]),
                            "TOTAL": float(linha["VALOR TOTAL"])
                        })
                    st.success(f"Orçamento Nº {num_o} de {cli_o} importado!")
                    st.rerun()
        else:
            st.info("✅ Todos os orçamentos já foram fechados ou não há orçamentos ABERTOS.")
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
    total_geral = sum(it['TOTAL'] for it in st.session_state.cesta)
    
    for i, item in enumerate(st.session_state.cesta):
        with st.container(border=True):
            cols = st.columns([4, 1, 1])
            cols[0].write(f"**{i+1}. {item['ITEM']}**")
            cols[0].write(f"R$ {item['UNIT']:,.2f} x {item['QTD']} = **R$ {item['TOTAL']:,.2f}**")
            if cols[1].button("➖", key=f"m_{i}"):
                if item['QTD'] > 1:
                    st.session_state.cesta[i]['QTD'] -= 1
                    st.session_state.cesta[i]['TOTAL'] = st.session_state.cesta[i]['QTD'] * item['UNIT']
                else: st.session_state.cesta.pop(i)
                st.rerun()
            if cols[2].button("🗑️", key=f"d_{i}"):
                st.session_state.cesta.pop(i)
                st.rerun()

    st.info(f"#### 💰 TOTAL GERAL DA VENDA: R$ {total_geral:,.2f}")

    # --- 4. PARCELAMENTO PROGRAMÁVEL ---
    st.divider()
    st.subheader("🏦 Faturamento Programável")
    
    with st.container(border=True):
        col_f1, col_f2 = st.columns([1, 1])
        num_parcelas = col_f1.number_input("Dividir em quantas parcelas?", min_value=1, max_value=6, value=1)
        status_inicial = col_f2.selectbox("Status dos Lançamentos", ["PENDENTE", "RECEBIDO"])
        
        dados_parcelas = []
        soma_atual = 0.0
        
        st.write("---")
        for i in range(int(num_parcelas)):
            c1, c2, c3 = st.columns([1, 2, 2])
            c1.markdown(f"<br>**{i+1}ª Parc.**", unsafe_allow_html=True)
            dt = c2.date_input(f"Vencimento", datetime.now(), key=f"dt_{i}")
            # Sugere o valor restante na primeira parcela ou valor zerado nas outras
            sugestao = total_geral if i == 0 else 0.0
            val = c3.number_input(f"Valor (R$)", min_value=0.0, value=float(sugestao), format="%.2f", key=f"val_{i}")
            
            dados_parcelas.append({"DATA": dt, "VALOR": val, "PARCELA": f"{i+1}/{num_parcelas}"})
            soma_atual += val

        # Feedback do valor restante
        restante = round(total_geral - soma_atual, 2)
        if restante == 0:
            st.success("✅ Total das parcelas confere com o total da venda!")
        elif restante > 0:
            st.warning(f"⚠️ Falta distribuir: **R$ {restante:,.2f}**")
        else:
            st.error(f"❌ Valor ultrapassou o total em: **R$ {abs(restante):,.2f}**")

 # --- 5. BOTÃO FINALIZAR TUDO ---
    pode_finalizar = (restante == 0)
    
    if st.button("🚀 FINALIZAR VENDA E GERAR FINANCEIRO", use_container_width=True, type="primary", disabled=not pode_finalizar):
        try:
            vendedor_atual = st.session_state.get('usuario', 'SISTEMA')
            
            # A. Salvar na aba Vendas
            df_vendas_db = conn.read(worksheet="Vendas", ttl=0).dropna(how='all')
            
            # --- GARANTIA CONTRA KEYERROR: Limpa espaços e coloca em maiúsculo ---
            df_vendas_db.columns = df_vendas_db.columns.str.strip().str.upper()
            
            novas_vendas = []
            for it in st.session_state.cesta:
                # Busca o custo do produto
                dados_prod = df_produtos[df_produtos['PRODUTO'] == it["ITEM"]]
                
                custo_unitario = 0.0
                if not dados_prod.empty:
                    # Tenta pegar 'CUSTO TOTAL', se não achar, usa 0
                    custo_unitario = float(dados_prod.iloc[0].get('CUSTO TOTAL', 0))
                
                custo_total_venda = custo_unitario * it["QTD"]
                margem_venda = it["TOTAL"] - custo_total_venda

                novas_vendas.append({
                    "DATA": datetime.now().strftime("%d/%m/%Y"),
                    "CLIENTE": cliente_final,
                    "PRODUTO": it["ITEM"],
                    "QTD": it["QTD"],
                    "VALOR UNIT": it["UNIT"],
                    "TOTAL": it["TOTAL"],
                    "VENDEDOR": vendedor_atual,
                    "CUSTO": custo_total_venda,
                    "MARGEM": margem_venda
                })
            
            df_venda_final = pd.concat([df_vendas_db, pd.DataFrame(novas_vendas)], ignore_index=True)
            conn.update(worksheet="Vendas", data=df_venda_final)

            # B. Salvar no Fluxo de Caixa
            df_caixa = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
            df_caixa.columns = df_caixa.columns.str.strip().str.upper()
            
            novos_lancamentos = []
            for parc in dados_parcelas:
                novos_lancamentos.append({
                    "DATA": parc["DATA"].strftime("%d/%m/%Y"),
                    "TIPO": "ENTRADA",
                    "DESCRICAO": f"VENDA - {cliente_final}".upper(),
                    "VALOR": parc["VALOR"],
                    "PARCELA": parc["PARCELA"],
                    "STATUS": status_inicial,
                    "CLIENTE": cliente_final
                })
            df_caixa_final = pd.concat([df_caixa, pd.DataFrame(novos_lancamentos)], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_caixa_final)

            # C. Mudar Status do Orçamento para FECHADO
            if 'num_orc_venda' in st.session_state:
                num_venda = str(st.session_state.num_orc_venda)
                df_orc_upd = conn.read(worksheet="Orcamentos", ttl=0)
                df_orc_upd.columns = df_orc_upd.columns.str.strip().str.upper()
                
                # Aplica o status FECHADO
                df_orc_upd.loc[df_orc_upd['NUMERO'].astype(str) == num_venda, 'STATUS'] = "FECHADO"
                conn.update(worksheet="Orcamentos", data=df_orc_upd)

            # D. Finalização de Interface
            st.success(f"🎉 Venda realizada! Orçamento {st.session_state.get('num_orc_venda', '')} fechado com sucesso.")
            st.balloons()
            
            # Limpa a memória para a próxima venda
            st.session_state.cesta = []
            if 'num_orc_venda' in st.session_state:
                del st.session_state.num_orc_venda
            if 'cliente_venda' in st.session_state:
                st.session_state.cliente_venda = "Nenhum selecionado"
            
            # Rerun apenas no final de tudo
            st.rerun()

        except Exception as e:
            st.error(f"Erro ao processar a venda: {e}")