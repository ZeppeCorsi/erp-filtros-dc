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

# --- CARREGAMENTO E TRATAMENTO SEPARADO ---
try:
    # 1. Lendo as abas
    df_fluxo_raw = conn.read(worksheet="Fluxo de Caixa", ttl=0)
    df_gastos_raw = conn.read(worksheet="Gastos Fixos", ttl=0)

    # 2. Tratando FLUXO DE CAIXA (Tem STATUS e TIPO)
    df_fluxo = df_fluxo_raw.copy()
    df_fluxo.columns = [str(c).strip().upper() for c in df_fluxo.columns]
    
    # Garantir que as colunas essenciais existem no Fluxo
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
    df_fluxo['STATUS'] = df_fluxo['STATUS'].astype(str).str.strip().upper()
    df_fluxo['TIPO'] = df_fluxo['TIPO'].astype(str).str.strip().upper()
    if 'NF' not in df_fluxo.columns: df_fluxo['NF'] = ""

    # 3. Tratando GASTOS FIXOS (Só DATA, VALOR e DETALHE - conforme sua imagem)
    df_gastos_fixos = df_gastos_raw.copy()
    df_gastos_fixos.columns = [str(c).strip().upper() for c in df_gastos_fixos.columns]
    
    # Converte o VALOR dos gastos fixos (Coluna B da sua imagem)
    df_gastos_fixos['VALOR'] = pd.to_numeric(df_gastos_fixos['VALOR'], errors='coerce').fillna(0)

    # --- 4. INTERFACE ---
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    # Cálculos de Saldo
    recebido = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    pago = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_atual = recebido - pago

    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo Real", f"R$ {saldo_atual:,.2f}")
    c2.metric("A Receber", f"R$ {df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum():,.2f}")
    c3.metric("A Pagar", f"R$ {df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum():,.2f}")

    st.divider()

    t1, t2, t3 = st.tabs(["📄 Extrato", "✅ Baixa / NF", "⚙️ Gerar Mensalidade"])

    with t1:
        st.dataframe(df_fluxo[['DATA', 'CLIENTE', 'VALOR', 'STATUS', 'NF']].sort_index(ascending=False), use_container_width=True)

    with t2:
        df_pend = df_fluxo[df_fluxo['STATUS'] == 'PENDENTE'].copy()
        if not df_pend.empty:
            opcoes = df_pend.apply(lambda x: f"{x['CLIENTE']} | R$ {x['VALOR']:.2f}", axis=1).tolist()
            escolha = st.selectbox("Dar baixa em:", opcoes)
            nova_nf = st.text_input("Número da NF:")
            
            if st.button("Confirmar Baixa"):
                idx = df_pend.index[opcoes.index(escolha)]
                tipo = df_fluxo.at[idx, 'TIPO']
                df_fluxo.at[idx, 'STATUS'] = "RECEBIDO" if tipo == "ENTRADA" else "PAGO"
                if nova_nf: df_fluxo.at[idx, 'NF'] = nova_nf
                
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo)
                st.success("Baixa realizada!")
                st.rerun()
        else:
            st.info("Nada pendente.")

    with t3:
        st.subheader("Lançar Gastos do Mês")
        mes = st.selectbox("Mês de Ref.", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
        if st.button("Lançar Gastos Fixos"):
            novos = []
            for _, g in df_gastos_fixos.iterrows():
                novos.append({
                    "DATA": datetime.now().strftime("%d/%m/%Y"),
                    "TIPO": "SAIDA",
                    "CLIENTE": f"{g['DETALHE']} ({mes})", # Usa a coluna DETALHE da sua imagem
                    "VALOR": g['VALOR'],
                    "STATUS": "PENDENTE",
                    "NF": ""
                })
            df_up = pd.concat([df_fluxo, pd.DataFrame(novos)], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_up)
            st.success("Gastos lançados no Fluxo!")
            st.rerun()

except Exception as e:
    st.error(f"Erro: {e}")