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

st.title("🏦 Controle de Pequeno Caixa (Fundo Fixo)")

# --- 2. LÓGICA DE SALDO ---
# Buscamos adiantamentos no Fluxo de Caixa e Gastos na nova planilha
try:
    df_principal = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
    df_gastos = conn.read(worksheet="Pequeno Caixa", ttl=0).dropna(how='all')
    
    # Soma o que saiu do banco como Adiantamento
    total_adiantado = pd.to_numeric(df_principal[df_principal['DESCRICAO'].str.contains("ADIANTAMENTO", na=False)]['VALOR']).sum()
    
    # Soma os gastos detalhados da nova planilha
    total_gasto_detalhado = pd.to_numeric(df_gastos['VALOR']).sum()
    
    saldo_em_maos = total_adiantado - total_gasto_detalhado

    c1, c2, c3 = st.columns(3)
    c1.metric("Dinheiro Sacado (Banco)", f"R$ {total_adiantado:,.2f}")
    c2.metric("Gastos Realizados (Notas)", f"R$ {total_gasto_detalhado:,.2f}", delta=f"-{total_gasto_detalhado:,.2f}", delta_color="inverse")
    c3.metric("Saldo Disponível em Mãos", f"R$ {saldo_em_maos:,.2f}")
except:
    st.warning("Certifique-se de que a aba 'Pequeno Caixa' existe na planilha.")

st.divider()

# --- 3. LANÇAMENTO DE GASTO ---
st.subheader("📝 Lançar Gasto da Nota Fiscal")
with st.container(border=True):
    with st.form("form_gasto_extra", clear_on_submit=True):
        col1, col2 = st.columns(2)
        desc = col1.text_input("Descrição (O que comprou?)").upper()
        valor = col2.number_input("Valor da Nota (R$)", min_value=0.0, format="%.2f")
        
        data_g = col1.date_input("Data da Nota", datetime.now())
        foto = st.file_uploader("📷 Foto do Recibo/Cupom", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("SALVAR GASTO NO PEQUENO CAIXA"):
            if desc and valor > 0:
                nome_arquivo = "sem_foto"
                if foto:
                    nome_arquivo = f"NOTA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    with open(f"comprovantes/{nome_arquivo}", "wb") as f:
                        f.write(foto.getbuffer())
                
                # SALVA APENAS NA ABA PEQUENO CAIXA
                novo_item = pd.DataFrame([{
                    "DATA": data_g.strftime("%d/%m/%Y"),
                    "DESCRICAO": desc,
                    "VALOR": valor,
                    "FOTO": nome_arquivo
                }])
                
                df_p_caixa = conn.read(worksheet="Pequeno Caixa", ttl=0).dropna(how='all')
                conn.update(worksheet="Pequeno Caixa", data=pd.concat([df_p_caixa, novo_item], ignore_index=True))
                
                st.success("Gasto registrado com sucesso!")
                st.rerun()

# --- 4. HISTÓRICO COM FOTOS ---
st.subheader("📑 Histórico de Notas")
if not df_gastos.empty:
    # Mostra os últimos 10 gastos
    for i, row in df_gastos.tail(10).iterrows():
        with st.expander(f"{row['DATA']} - {row['DESCRICAO']} - R$ {row['VALOR']:.2f}"):
            if str(row['FOTO']) != "sem_foto" and os.path.exists(f"comprovantes/{row['FOTO']}"):
                st.image(f"comprovantes/{row['FOTO']}", width=400)
            else:
                st.info("Sem foto disponível.")