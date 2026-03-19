import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Financeiro | Filtros DC", layout="wide")

# 2. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Por favor, faça o login na página principal.")
    st.stop()

# 3. CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- CARREGAMENTO E TRATAMENTO DE DADOS ---
try:
    # Lendo as abas
    df_fluxo_raw = conn.read(worksheet="Fluxo de Caixa", ttl=0)
    df_gastos_raw = conn.read(worksheet="Gastos Fixos", ttl=0)

    # 🛠️ LIMPEZA BRUTA DE COLUNAS (Para matar o erro 'VALOR')
    # Isso remove aspas, espaços e deixa tudo em MAIÚSCULO
    df_fluxo = df_fluxo_raw.copy()
    df_fluxo.columns = [str(c).strip().upper().replace('"', '').replace("'", "") for c in df_fluxo.columns]
    
    df_gastos_fixos = df_gastos_raw.copy()
    df_gastos_fixos.columns = [str(c).strip().upper().replace('"', '').replace("'", "") for c in df_gastos_fixos.columns]

    # Agora o Python VAI achar 'VALOR'
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
    df_gastos_fixos['VALOR'] = pd.to_numeric(df_gastos_fixos['VALOR'], errors='coerce').fillna(0)

    # Garante que a coluna NF existe (Coluna H na sua imagem)
    if 'NF' not in df_fluxo.columns:
        df_fluxo['NF'] = ""

    # 4. DASHBOARD DE SALDO
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    # Filtros de Status (Garantindo que o nome do status também esteja limpo)
    df_fluxo['STATUS'] = df_fluxo['STATUS'].str.strip().upper()
    df_fluxo['TIPO'] = df_fluxo['TIPO'].str.strip().upper()

    recebido = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    pago = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_atual = recebido - pago

    a_receber = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    a_pagar = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo Real (Extrato)", f"R$ {saldo_atual:,.2f}")
    c2.metric("A Receber", f"R$ {a_receber:,.2f}")
    c3.metric("A Pagar", f"R$ {a_pagar:,.2f}", delta=f"-{a_pagar:,.2f}", delta_color="inverse")

    st.divider()

    # 5. ABAS
    tab_extrato, tab_baixa, tab_fixos = st.tabs(["📄 Extrato", "✅ Dar Baixa / NF", "⚙️ Gerar Mensalidade"])

    with tab_extrato:
        # Mostra as colunas que você tem na planilha
        colunas_ver = [c for c in ['DATA', 'TIPO', 'CLIENTE', 'VALOR', 'STATUS', 'NF'] if c in df_fluxo.columns]
        st.dataframe(df_fluxo[colunas_ver].sort_index(ascending=False), use_container_width=True)

    with tab_baixa:
        st.subheader("Confirmar Recebimento ou Pagamento")
        # Filtramos antes do botão para o VS Code não dar erro
        df_pendentes = df_fluxo[df_fluxo['STATUS'] == 'PENDENTE'].copy()

        if not df_pendentes.empty:
            opcoes = df_pendentes.apply(lambda x: f"{x['DATA']} - {x['CLIENTE']} | R$ {x['VALOR']:.2f}", axis=1).tolist()
            selecionado = st.selectbox("Selecione o lançamento:", opcoes)
            nf_input = st.text_input("Vincular Número da NF (opcional):")

            if st.button("Confirmar Baixa"):
                idx_orig = df_pendentes.index[opcoes.index(selecionado)]
                tipo_item = df_fluxo.at[idx_orig, 'TIPO']
                
                df_fluxo.at[idx_orig, 'STATUS'] = "RECEBIDO" if tipo_item == "ENTRADA" else "PAGO"
                if nf_input:
                    df_fluxo.at[idx_orig, 'NF'] = nf_input
                
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo)
                st.success("Baixa realizada!")
                st.rerun()
        else:
            st.info("Nada pendente!")

    with tab_fixos:
        # Bloco dos Gastos Fixos
        st.subheader("Gerar Gastos do Mês")
        mes_ref = st.selectbox("Mês:", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
        if st.button("Lançar Agora"):
            novos = []
            for _, g in df_gastos_fixos.iterrows():
                novos.append({"DATA": datetime.now().strftime("%d/%m/%Y"), "TIPO": "SAIDA", "CLIENTE": f"{g['ITEM']} ({mes_ref})", "VALOR": g['VALOR'], "STATUS": "PENDENTE", "NF": ""})
            df_final = pd.concat([df_fluxo, pd.DataFrame(novos)], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_final)
            st.success("Lançado!")
            st.rerun()

except Exception as e:
    st.error(f"Erro ao processar: {e}")