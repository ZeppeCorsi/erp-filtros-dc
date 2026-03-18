import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os

# 1. PASTA DE FOTOS
if not os.path.exists("comprovantes"):
    os.makedirs("comprovantes")

st.set_page_config(page_title="Pequeno Caixa | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🏦 Extrato de Pequeno Caixa (Fundo Fixo)")

# --- 2. CARREGAMENTO E LÓGICA DE SALDO ---
try:
    # Busca Adiantamentos no Fluxo de Caixa Principal
    df_principal = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
    df_adiantamentos = df_principal[df_principal['DESCRICAO'].str.contains("ADIANTAMENTO", na=False)].copy()
    df_adiantamentos['VALOR'] = pd.to_numeric(df_adiantamentos['VALOR'])
    df_adiantamentos['TIPO_MOV'] = "➕ ADIANTAMENTO"

    # Busca Gastos na planilha Pequeno Caixa
    df_gastos = conn.read(worksheet="Pequeno Caixa", ttl=0).dropna(how='all')
    df_gastos['VALOR'] = pd.to_numeric(df_gastos['VALOR'])
    df_gastos['TIPO_MOV'] = "➖ GASTO"

    # Criar Extrato Unificado para Cálculo
    extrato = pd.concat([
        df_adiantamentos[['DATA', 'DESCRICAO', 'VALOR', 'TIPO_MOV']],
        df_gastos[['DATA', 'DESCRICAO', 'VALOR', 'TIPO_MOV']]
    ])
    
    # Converte data para ordenar corretamente
    extrato['DATA_DT'] = pd.to_datetime(extrato['DATA'], format='%d/%m/%Y')
    extrato = extrato.sort_values(by='DATA_DT', ascending=False)

    total_in = df_adiantamentos['VALOR'].sum()
    total_out = df_gastos['VALOR'].sum()
    saldo_atual = total_in - total_out

    # Dashboard de Cabeçalho
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Aportes", f"R$ {total_in:,.2f}")
    c2.metric("Total Gasto", f"R$ {total_out:,.2f}", delta=f"-{total_out:,.2f}", delta_color="inverse")
    c3.metric("SALDO DISPONÍVEL", f"R$ {saldo_atual:,.2f}")

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    saldo_atual = 0

st.divider()

# --- 3. ABAS DE OPERAÇÃO ---
tab_extrato, tab_novo_gasto = st.tabs(["📑 Extrato e Saldos", "💸 Lançar Novo Gasto"])

with tab_extrato:
    st.subheader("Histórico de Movimentações")
    if not extrato.empty:
        # Exibição do extrato formatado
        for _, row in extrato.iterrows():
            cor = "green" if row['TIPO_MOV'] == "➕ ADIANTAMENTO" else "red"
            simbolo = "+" if row['TIPO_MOV'] == "➕ ADIANTAMENTO" else "-"
            
            with st.expander(f"{row['DATA']} | {row['TIPO_MOV']} | {row['DESCRICAO']} | :[{cor}][{simbolo} R$ {row['VALOR']:,.2f}]"):
                # Se for um gasto, tenta mostrar a foto
                if row['TIPO_MOV'] == "➖ GASTO":
                    # Busca a foto correspondente no df_gastos original
                    foto_info = df_gastos[(df_gastos['DATA'] == row['DATA']) & (df_gastos['DESCRICAO'] == row['DESCRICAO'])]['FOTO'].values
                    if len(foto_info) > 0 and foto_info[0] != "sem_foto":
                        if os.path.exists(f"comprovantes/{foto_info[0]}"):
                            st.image(f"comprovantes/{foto_info[0]}", width=350, caption="Comprovante da Despesa")
                        else:
                            st.warning("Arquivo de imagem não encontrado no servidor.")
                    else:
                        st.info("Nenhum comprovante anexado.")
    else:
        st.info("Nenhuma movimentação encontrada.")

with tab_novo_gasto:
    st.subheader("Registrar Despesa")
    if saldo_atual <= 0:
        st.error("⚠️ Saldo Insuficiente! Solicite um adiantamento antes de lançar gastos.")
    
    with st.form("form_gasto_pequeno", clear_on_submit=True):
        col1, col2 = st.columns(2)
        desc_g = col1.text_input("O que foi pago?").upper()
        val_g = col2.number_input("Valor da Nota (R$)", min_value=0.0, max_value=float(saldo_atual) if saldo_atual > 0 else 0.01, format="%.2f")
        data_g = col1.date_input("Data da Despesa", datetime.now())
        foto_g = st.file_uploader("Anexar Comprovante", type=['jpg', 'jpeg', 'png'])
        
        if st.form_submit_button("Confirmar Pagamento"):
            if desc_g and val_g > 0:
                nome_f = "sem_foto"
                if foto_g:
                    nome_f = f"NOTA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    with open(f"comprovantes/{nome_f}", "wb") as f:
                        f.write(foto_g.getbuffer())
                
                # Salva na planilha específica de gastos
                novo_g = pd.DataFrame([{
                    "DATA": data_g.strftime("%d/%m/%Y"),
                    "DESCRICAO": desc_g,
                    "VALOR": val_g,
                    "FOTO": nome_f
                }])
                
                df_db_gastos = conn.read(worksheet="Pequeno Caixa", ttl=0).dropna(how='all')
                conn.update(worksheet="Pequeno Caixa", data=pd.concat([df_db_gastos, novo_g], ignore_index=True))
                
                st.success("Gasto abatido do saldo com sucesso!")
                st.rerun()

st.sidebar.markdown(f"**Saldo do Caixinha:** R$ {saldo_atual:,.2f}")