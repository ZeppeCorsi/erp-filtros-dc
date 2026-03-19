import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Financeiro | Filtros DC", layout="wide")

# 2. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça o login na home.")
    st.stop()

# 3. CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- CARREGAMENTO E TRATAMENTO SEPARADO ---
try:
    df_fluxo_raw = conn.read(worksheet="Fluxo de Caixa", ttl=0)
    df_gastos_raw = conn.read(worksheet="Gastos Fixos", ttl=0)

    # --- TRATANDO FLUXO DE CAIXA ---
    df_fluxo = df_fluxo_raw.copy()
    df_fluxo.columns = [str(c).strip().upper() for c in df_fluxo.columns]
    
    # Converte valor para número
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
    
    # CORREÇÃO DO ERRO 'UPPER': Usamos .str.upper() para colunas inteiras
    if 'STATUS' in df_fluxo.columns:
        df_fluxo['STATUS'] = df_fluxo['STATUS'].astype(str).str.strip().str.upper()
    if 'TIPO' in df_fluxo.columns:
        df_fluxo['TIPO'] = df_fluxo['TIPO'].astype(str).str.strip().str.upper()
    
    if 'NF' not in df_fluxo.columns:
        df_fluxo['NF'] = ""

    # --- TRATANDO GASTOS FIXOS (Conforme sua imagem image_aacce1.png) ---
    df_gastos_fixos = df_gastos_raw.copy()
    df_gastos_fixos.columns = [str(c).strip().upper() for c in df_gastos_fixos.columns]
    df_gastos_fixos['VALOR'] = pd.to_numeric(df_gastos_fixos['VALOR'], errors='coerce').fillna(0)

    # --- 4. DASHBOARD ---
# --- FILTRO DE EXTRATO (TIPO BANCÁRIO) ---
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    # Criamos as opções de Meses baseados nas datas que existem na planilha
    df_fluxo['DT_OBJ'] = pd.to_datetime(df_fluxo['DATA'], dayfirst=True, errors='coerce')
    df_fluxo = df_fluxo.dropna(subset=['DT_OBJ']).sort_values('DT_OBJ') # Ordena cronológico
    
    # Criar lista de meses disponíveis: "Março/2026"
    df_fluxo['MES_REF'] = df_fluxo['DT_OBJ'].dt.strftime('%m/%Y')
    meses_disponiveis = ["Tudo"] + sorted(df_fluxo['MES_REF'].unique().tolist(), key=lambda x: datetime.strptime(x, '%m/%Y'))
    
    col_f1, col_f2 = st.columns([2, 4])
    mes_filtro = col_f1.selectbox("Selecione o período do extrato:", meses_disponiveis, index=len(meses_disponiveis)-1)

    # Filtragem dos dados
    if mes_filtro == "Tudo":
        df_exibir = df_fluxo.copy()
    else:
        df_exibir = df_fluxo[df_fluxo['MES_REF'] == mes_filtro].copy()

    # --- MÉTRICAS (Baseadas no filtro selecionado) ---
    recebido = df_exibir[(df_exibir['TIPO'] == 'ENTRADA') & (df_exibir['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    pago = df_exibir[(df_exibir['TIPO'] == 'SAIDA') & (df_exibir['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_periodo = recebido - pago

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Saldo Real ({mes_filtro})", f"R$ {saldo_periodo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    a_receber = df_exibir[(df_exibir['TIPO'] == 'ENTRADA') & (df_exibir['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    c2.metric("A Receber no período", f"R$ {a_receber:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    a_pagar = df_exibir[(df_exibir['TIPO'] == 'SAIDA') & (df_exibir['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    c3.metric("A Pagar no período", f"R$ {a_pagar:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.divider()

    # --- ABAS ---
    t1, t2, t3, t4 = st.tabs(["📄 Extrato Detalhado", "📅 Previsão Futura", "✅ Baixa / NF", "⚙️ Lançar Gasto Fixo"])

    with t1:
        st.subheader(f"Movimentações: {mes_filtro}")
        # Formata a coluna VALOR apenas para exibição na tabela
        df_tab = df_exibir[['DATA', 'TIPO', 'CLIENTE', 'VALOR', 'STATUS', 'NF']].copy()
        df_tab['VALOR'] = df_tab['VALOR'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.dataframe(df_tab, use_container_width=True, hide_index=True)

    with t2:
        st.subheader("O que ainda vai acontecer")
        previsao = df_exibir[df_exibir['STATUS'] == 'PENDENTE'].copy()
        if not previsao.empty:
            previsao['VALOR'] = previsao['VALOR'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(previsao[['DATA', 'TIPO', 'CLIENTE', 'VALOR']], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma pendência para o período selecionado.")

    with t3:
        st.subheader("Dar Baixa Individual")
        df_pend = df_exibir[df_exibir['STATUS'] == 'PENDENTE'].copy()
        if not df_pend.empty:
            opcoes = df_pend.apply(lambda x: f"{x['DATA']} | {x['CLIENTE']} (R$ {x['VALOR']:.2f})", axis=1).tolist()
            escolha = st.selectbox("Selecione o item:", opcoes)
            nova_nf = st.text_input("Vincular NF (Opcional):")
            
            if st.button("Confirmar Pagamento/Recebimento"):
                idx_orig = df_pend.index[opcoes.index(escolha)]
                tipo_item = df_fluxo.at[idx_orig, 'TIPO']
                df_fluxo.at[idx_orig, 'STATUS'] = "RECEBIDO" if tipo_item == "ENTRADA" else "PAGO"
                if nova_nf: df_fluxo.at[idx_orig, 'NF'] = nova_nf
                
                # Salva na planilha mantendo as colunas originais (sem as de ajuda DT_OBJ)
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo.drop(columns=['DT_OBJ', 'MES_REF']))
                st.success("Baixa realizada com sucesso!")
                st.rerun()
        else:
            st.info("Nada para baixar neste mês.")

    with t4:
        st.subheader("Lançar Item dos Gastos Fixos")
        item_fixo = st.selectbox("Selecione o custo:", df_gastos_fixos['DETALHE'].tolist())
        valor_base = df_gastos_fixos[df_gastos_fixos['DETALHE'] == item_fixo]['VALOR'].values[0]
        
        col1, col2 = st.columns(2)
        novo_valor = col1.number_input("Confirmar Valor:", value=float(valor_base))
        nova_data = col2.date_input("Data de Vencimento:", datetime.now())
        
        if st.button("Enviar para Fluxo de Caixa"):
            novo_lanc = pd.DataFrame([{
                "DATA": nova_data.strftime("%d/%m/%Y"),
                "TIPO": "SAIDA",
                "CLIENTE": item_fixo,
                "VALOR": novo_valor,
                "STATUS": "PENDENTE",
                "NF": ""
            }])
            df_final = pd.concat([df_fluxo.drop(columns=['DT_OBJ', 'MES_REF']), novo_lanc], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_final)
            st.success(f"{item_fixo} lançado!")
            st.rerun()

except Exception as e:
    st.error(f"Erro ao processar dados: {e}")