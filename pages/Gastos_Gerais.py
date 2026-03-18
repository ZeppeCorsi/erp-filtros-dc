import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import os

# 1. CONFIGURAÇÕES INICIAIS E PASTAS
if not os.path.exists("comprovantes"):
    os.makedirs("comprovantes")

if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

st.set_page_config(page_title="Pequeno Caixa | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÃO DE CARREGAMENTO E CÁLCULO DE SALDO ---
def carregar_dados_caixinha():
    try:
        # Lendo Fluxo de Caixa (Para buscar Adiantamentos)
        df_fluxo = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
        df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
        
        # Filtra aportes que entraram no caixinha
        df_aportes = df_fluxo[df_fluxo['DESCRICAO'].str.contains("ADIANTAMENTO", na=False)].copy()
        df_aportes['TIPO_MOV'] = "➕ ADIANTAMENTO"

        # Lendo Pequeno Caixa (Para buscar Gastos)
        df_gastos = conn.read(worksheet="Pequeno Caixa", ttl=0).dropna(how='all')
        df_gastos['VALOR'] = pd.to_numeric(df_gastos['VALOR'], errors='coerce').fillna(0)
        df_gastos['TIPO_MOV'] = "➖ GASTO"

        # Criar Extrato Unificado
        extrato_unificado = pd.concat([
            df_aportes[['DATA', 'DESCRICAO', 'VALOR', 'TIPO_MOV']],
            df_gastos[['DATA', 'DESCRICAO', 'VALOR', 'TIPO_MOV']]
        ])
        
        # Ordenação por data (da mais recente para a antiga)
        extrato_unificado['DATA_DT'] = pd.to_datetime(extrato_unificado['DATA'], format='%d/%m/%Y', errors='coerce')
        extrato_unificado = extrato_unificado.sort_values(by='DATA_DT', ascending=False)

        saldo = df_aportes['VALOR'].sum() - df_gastos['VALOR'].sum()
        
        return extrato_unificado, saldo, df_gastos
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return pd.DataFrame(), 0.0, pd.DataFrame()

extrato, saldo_atual, df_gastos_raw = carregar_dados_caixinha()

# --- 3. DASHBOARD DE SALDO ---
st.title("🏦 Gestão de Pequeno Caixa")
c1, c2, c3 = st.columns(3)
c1.metric("Saldo Atual em Mãos", f"R$ {saldo_atual:,.2f}")
c2.write("") # Espaçador
c3.info(f"O saldo é calculado automaticamente: (Aportes no Fluxo de Caixa) - (Gastos no Pequeno Caixa).")

st.divider()

# --- 4. INTERFACE DE ABAS ---
tab1, tab2, tab3 = st.tabs(["📑 Extrato e Comprovantes", "💸 Lançar Gasto", "💰 Registrar Aporte"])

# --- ABA 1: EXTRATO ---
with tab1:
    st.subheader("Histórico de Movimentações")
    if not extrato.empty:
        for _, row in extrato.iterrows():
            # Estilização visual
            cor = "green" if row['TIPO_MOV'] == "➕ ADIANTAMENTO" else "red"
            simbolo = "+" if row['TIPO_MOV'] == "➕ ADIANTAMENTO" else "-"
            
            with st.expander(f"{row['DATA']} | {row['TIPO_MOV']} | {row['DESCRICAO']} | :[{cor}][{simbolo} R$ {row['VALOR']:,.2f}]"):
                if row['TIPO_MOV'] == "➖ GASTO":
                    # Tenta localizar a foto na planilha original de gastos
                    match_foto = df_gastos_raw[(df_gastos_raw['DATA'] == row['DATA']) & 
                                              (df_gastos_raw['DESCRICAO'] == row['DESCRICAO'])]['FOTO'].values
                    if len(match_foto) > 0 and str(match_foto[0]) != "sem_foto":
                        if os.path.exists(f"comprovantes/{match_foto[0]}"):
                            st.image(f"comprovantes/{match_foto[0]}", width=400)
                        else: st.warning("Imagem não encontrada na pasta 'comprovantes'.")
                    else: st.info("Gasto sem comprovante anexado.")
    else:
        st.info("Nenhuma movimentação registrada até o momento.")

# --- ABA 2: LANÇAR GASTO ---
with tab2:
    st.subheader("Novo Gasto (Abater do Saldo)")
    if saldo_atual <= 0:
        st.error("⚠️ Você não possui saldo para lançar gastos. Registre um aporte primeiro.")
    else:
        with st.form("form_novo_gasto", clear_on_submit=True):
            col_g1, col_g2 = st.columns(2)
            desc_gasto = col_g1.text_input("Descrição (Ex: Café, Motoboy, Limpeza)").upper()
            data_gasto = col_g2.date_input("Data do Gasto", datetime.now())
            
            val_gasto = col_g1.number_input("Valor da Nota (R$)", min_value=0.0, max_value=float(saldo_atual), format="%.2f")
            foto_gasto = col_g2.file_uploader("📷 Tirar foto ou anexar recibo", type=['png', 'jpg', 'jpeg'])
            
            if st.form_submit_button("🚀 SALVAR GASTO"):
                if desc_gasto and val_gasto > 0:
                    nome_arquivo = "sem_foto"
                    if foto_gasto:
                        nome_arquivo = f"NOTA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        with open(f"comprovantes/{nome_arquivo}", "wb") as f:
                            f.write(foto_gasto.getbuffer())
                    
                    # Salva na aba Pequeno Caixa
                    novo_gasto_df = pd.DataFrame([{
                        "DATA": data_gasto.strftime("%d/%m/%Y"),
                        "DESCRICAO": desc_gasto,
                        "VALOR": val_gasto,
                        "FOTO": nome_arquivo
                    }])
                    
                    df_db_pequeno = conn.read(worksheet="Pequeno Caixa", ttl=0).dropna(how='all')
                    conn.update(worksheet="Pequeno Caixa", data=pd.concat([df_db_pequeno, novo_gasto_df], ignore_index=True))
                    
                    st.success("✅ Gasto registrado e abatido do saldo!")
                    st.rerun()
                else:
                    st.warning("Preencha todos os campos obrigatórios.")

# --- ABA 3: NOVO APORTE ---
with tab3:
    st.subheader("💰 Novo Aporte (Entrada de Dinheiro)")
    st.info("Utilize esta aba quando retirar dinheiro do banco ou caixa central para o caixinha diário.")
    
    with st.form("form_novo_aporte"):
        col_a1, col_a2 = st.columns(2)
        v_aporte = col_a1.number_input("Valor Recebido (R$)", min_value=0.0, format="%.2f")
        d_aporte = col_a2.date_input("Data do Recebimento", datetime.now())
        origem_aporte = st.selectbox("Origem do Recurso", ["SAQUE BANCÁRIO", "DINHEIRO EM MÃOS", "REEMBOLSO"])
        
        if st.form_submit_button("➕ REGISTRAR APORTE"):
            if v_aporte > 0:
                try:
                    # Registra no Fluxo de Caixa Principal (SAÍDA do banco para o caixinha)
                    df_financeiro = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
                    
                    novo_lanc_financeiro = pd.DataFrame([{
                        "DATA": d_aporte.strftime("%d/%m/%Y"),
                        "TIPO": "SAIDA",
                        "DESCRICAO": f"ADIANTAMENTO PEQUENO CAIXA - {origem_aporte}",
                        "VALOR": v_aporte,
                        "PARCELA": "1/1",
                        "STATUS": "RECEBIDO",
                        "CLIENTE": "INTERNO"
                    }])
                    
                    df_final_fluxo = pd.concat([df_financeiro, novo_lanc_financeiro], ignore_index=True)
                    conn.update(worksheet="Fluxo de Caixa", data=df_final_fluxo)
                    
                    st.success(f"✅ R$ {v_aporte:,.2f} adicionados ao Pequeno Caixa!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)
st.sidebar.write(f"**Saldo Atual:** R$ {saldo_atual:,.2f}")