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
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    # Filtros para o Saldo Real
    recebido = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    pago = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_atual = recebido - pago

    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo Real (Extrato)", f"R$ {saldo_atual:,.2f}")
    
    a_receber = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    c2.metric("A Receber", f"R$ {a_receber:,.2f}")
    
    a_pagar = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    c3.metric("A Pagar", f"R$ {a_pagar:,.2f}")

    st.divider()

    # --- 5. ABAS ---
    t1, t2, t3 = st.tabs(["📄 Extrato", "✅ Dar Baixa / NF", "⚙️ Gerar Mensalidade"])

    with t1:
        st.subheader("Histórico de Movimentações")
        st.dataframe(df_fluxo[['DATA', 'CLIENTE', 'VALOR', 'STATUS', 'NF']].sort_index(ascending=False), use_container_width=True)

    with t2:
        st.subheader("Confirmar Recebimento/Pagamento")
        df_pend = df_fluxo[df_fluxo['STATUS'] == 'PENDENTE'].copy()
        
        if not df_pend.empty:
            opcoes = df_pend.apply(lambda x: f"{x['CLIENTE']} | R$ {x['VALOR']:.2f}", axis=1).tolist()
            escolha = st.selectbox("Selecione o lançamento:", opcoes)
            nova_nf = st.text_input("Número da NF (opcional):")
            
            if st.button("Confirmar Baixa"):
                idx = df_pend.index[opcoes.index(escolha)]
                tipo = df_fluxo.at[idx, 'TIPO']
                
                df_fluxo.at[idx, 'STATUS'] = "RECEBIDO" if tipo == "ENTRADA" else "PAGO"
                if nova_nf:
                    df_fluxo.at[idx, 'NF'] = nova_nf
                
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo)
                st.success("Baixa realizada e planilha atualizada!")
                st.rerun()
        else:
            st.info("Não há itens pendentes.")

    with t3:
        st.subheader("Gerar Gastos do Mês")
        mes = st.selectbox("Selecione o Mês:", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
        
        if st.button("Lançar Gastos Fixos"):
            novos_lancamentos = []
            for _, linha in df_gastos_fixos.iterrows():
                novos_lancamentos.append({
                    "DATA": datetime.now().strftime("%d/%m/%Y"),
                    "TIPO": "SAIDA",
                    "CLIENTE": f"{linha['DETALHE']} ({mes})",
                    "VALOR": linha['VALOR'],
                    "STATUS": "PENDENTE",
                    "NF": ""
                })
            
            df_atualizado = pd.concat([df_fluxo, pd.DataFrame(novos_lancamentos)], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_atualizado)
            st.success(f"Gastos de {mes} lançados como pendentes!")
            st.rerun()

except Exception as e:
    st.error(f"Erro inesperado: {e}")