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
# --- PROCESSAMENTO DE SALDO REAL (TODO O HISTÓRICO) ---
    # Isso garante que o saldo não fique errado ao mudar o mês
    total_entradas_hist = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    total_saidas_hist = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_real_hoje = total_entradas_hist - total_saidas_hist

    # --- FILTRO DE EXTRATO ---
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    col_f1, col_f2 = st.columns([2, 4])
    # Pegamos os meses disponíveis para o filtro
    meses_opcoes = ["Tudo"] + sorted(df_fluxo['MES_REF'].unique().tolist(), key=lambda x: datetime.strptime(x, '%m/%Y'))
    mes_filtro = col_f1.selectbox("Filtrar extrato por mês:", meses_opcoes, index=len(meses_opcoes)-1)

    # Dados que serão mostrados na tabela (filtrados)
    if mes_filtro == "Tudo":
        df_exibir = df_fluxo.copy()
    else:
        df_exibir = df_fluxo[df_fluxo['MES_REF'] == mes_filtro].copy()

    # --- MÉTRICAS DO PERÍODO SELECIONADO ---
    entradas_mes = df_exibir[(df_exibir['TIPO'] == 'ENTRADA') & (df_exibir['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    saidas_mes = df_exibir[(df_exibir['TIPO'] == 'SAIDA') & (df_exibir['STATUS'] == 'PAGO')]['VALOR'].sum()
    
    # Pendências APENAS do mês selecionado
    a_receber_mes = df_exibir[(df_exibir['TIPO'] == 'ENTRADA') & (df_exibir['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    a_pagar_mes = df_exibir[(df_exibir['TIPO'] == 'SAIDA') & (df_exibir['STATUS'] == 'PENDENTE')]['VALOR'].sum()

    # Exibição das métricas
    c1, c2, c3 = st.columns(3)
    
    # O Saldo Real é SEMPRE o saldo acumulado total da empresa (como no banco)
    c1.metric("Saldo Real Atual (Conta)", f"R$ {saldo_real_hoje:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    c2.metric(f"Entradas ({mes_filtro})", f"R$ {entradas_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric(f"Saídas ({mes_filtro})", f"R$ {saidas_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Nova linha de métricas para pendências
    st.write("---")
    cp1, cp2 = st.columns(2)
    cp1.metric(f"A Receber em {mes_filtro}", f"R$ {a_receber_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    cp2.metric(f"A Pagar em {mes_filtro}", f"R$ {a_pagar_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")

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