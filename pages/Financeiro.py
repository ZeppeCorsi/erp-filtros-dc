import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA PÁGINA (Sempre o primeiro)
st.set_page_config(page_title="Financeiro | Filtros DC", layout="wide")

# 2. SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Por favor, faça o login.")
    st.stop()

# 3. CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# Função de limpeza para evitar erros no futuro
def limpar_texto(texto):
    if not texto: return ""
    import unicodedata
    t = str(texto).replace("R$", "RS")
    nfkd = unicodedata.normalize('NFKD', t)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

# --- INÍCIO DA INTERFACE ---
st.title("🏦 Extrato e Conciliação Bancária")

# Carregar Dados
try:
    df_fluxo = conn.read(worksheet="Fluxo de Caixa", ttl=0)
    df_gastos_fixos = conn.read(worksheet="Gastos Fixos", ttl=0)
    
    # Converter valores para número
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
    df_gastos_fixos['VALOR'] = pd.to_numeric(df_gastos_fixos['VALOR'], errors='coerce').fillna(0)

    # 4. DASHBOARD DE SALDO
    entradas = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    saidas = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_real = entradas - saidas

    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo Real (Extrato)", f"R$ {saldo_real:,.2f}")
    
    pend_rec = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    c2.metric("A Receber", f"R$ {pend_rec:,.2f}")
    
    pend_pag = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    c3.metric("A Pagar", f"R$ {pend_pag:,.2f}", delta_color="inverse")

    st.divider()

    # 5. ABAS DE OPERAÇÃO
    tab_extrato, tab_baixa, tab_fixos = st.tabs(["📄 Extrato Detalhado", "✅ Dar Baixa", "⚙️ Gerar Gastos Fixos"])

    with tab_extrato:
        st.subheader("Movimentações")
        # Mostrar o mais recente primeiro
        st.dataframe(df_fluxo.sort_index(ascending=False), use_container_width=True)

    with tab_baixa:
        st.subheader("Confirmar Recebimento/Pagamento")
        df_pendentes = df_fluxo[df_fluxo['STATUS'] == 'PENDENTE']
        
        if not df_pendentes.empty:
            # Lista para seleção
            opcoes = df_pendentes.apply(lambda x: f"{x['CLIENTE']} | R$ {x['VALOR']:.2f} ({x['TIPO']})", axis=1).tolist()
            selecionado = st.selectbox("Selecione o item para dar baixa:", opcoes)
            
            if st.button("Confirmar Baixa"):
                idx_original = df_pendentes.index[opcoes.index(selecionado)]
                tipo = df_fluxo.at[idx_original, 'TIPO']
                novo_status = "RECEBIDO" if tipo == "ENTRADA" else "PAGO"
                
                # Atualiza local e na planilha
                df_fluxo.at[idx_original, 'STATUS'] = novo_status
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo)
                st.success(f"Baixa realizada com sucesso!")
                st.rerun()
        else:
            st.info("Não há contas pendentes.")

    with tab_fixos:
        st.subheader("Automação de Gastos Mensais")
        mes = st.selectbox("Mês de Referência", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
        
        if st.button("Lançar Gastos Fixos na Planilha"):
            novos = []
            for _, g in df_gastos_fixos.iterrows():
                novos.append({
                    "DATA": datetime.now().strftime("%d/%m/%Y"),
                    "TIPO": "SAIDA",
                    "DESCRICAO": f"{g['ITEM']} - {mes}",
                    "VALOR": g['VALOR'],
                    "PARCELA": "1/1",
                    "STATUS": "PENDENTE",
                    "CLIENTE": "GASTO FIXO"
                })
            
            df_final = pd.concat([df_fluxo, pd.DataFrame(novos)], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_final)
            st.success(f"Gastos de {mes} lançados!")
            st.rerun()

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")