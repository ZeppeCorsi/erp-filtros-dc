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

# 3. CONEXÃO E LIMPEZA DE TEXTO
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def limpar_para_sheets(texto):
    if not texto: return ""
    import unicodedata
    t = str(texto).replace("R$", "RS")
    nfkd = unicodedata.normalize('NFKD', t)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

# --- CARREGAMENTO E TRATAMENTO DE DADOS ---
try:
    # Lendo as abas
    df_fluxo = conn.read(worksheet="Fluxo de Caixa", ttl=0)
    df_gastos_fixos = conn.read(worksheet="Gastos Fixos", ttl=0)

    # Limpeza radical de nomes de colunas (Garante que 'VALOR' e 'STATUS' sejam achados)
    df_fluxo.columns = [str(c).strip().upper().replace('"', '') for c in df_fluxo.columns]
    df_gastos_fixos.columns = [str(c).strip().upper().replace('"', '') for c in df_gastos_fixos.columns]

    # Conversão de valores para números
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
    df_gastos_fixos['VALOR'] = pd.to_numeric(df_gastos_fixos['VALOR'], errors='coerce').fillna(0)

    # Garante que a coluna NF existe no DataFrame
    if 'NF' not in df_fluxo.columns:
        df_fluxo['NF'] = ""

    # 4. DASHBOARD DE SALDO (EXTRATO REAL)
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    # Saldo Real = Entradas Recebidas - Saídas Pagas
    recebido = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    pago = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_atual = recebido - pago

    # Previsões
    a_receber = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    a_pagar = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Saldo em Conta (Real)", f"R$ {saldo_atual:,.2f}")
    c2.metric("Total a Receber (Pendentes)", f"R$ {a_receber:,.2f}")
    c3.metric("Contas a Pagar (Pendentes)", f"R$ {a_pagar:,.2f}", delta=f"-{a_pagar:,.2f}", delta_color="inverse")

    st.divider()

    # 5. INTERFACE EM ABAS
    tab_extrato, tab_baixa, tab_fixos = st.tabs(["📄 Extrato", "✅ Dar Baixa / NF", "⚙️ Gerar Mensalidade"])

    with tab_extrato:
        st.subheader("Histórico de Movimentações")
        # Mostra as colunas principais e a NF
        exibir = df_fluxo[['DATA', 'TIPO', 'CLIENTE', 'VALOR', 'STATUS', 'NF']]
        st.dataframe(exibir.sort_index(ascending=False), use_container_width=True)

    with tab_baixa:
        st.subheader("Confirmar Recebimento ou Pagamento")
        df_pendentes = df_fluxo[df_fluxo['STATUS'] == 'PENDENTE']

        if not df_pendentes.empty:
            opcoes = df_pendentes.apply(lambda x: f"{x['DATA']} - {x['CLIENTE']} | R$ {x['VALOR']:.2f}", axis=1).tolist()
            selecionado = st.selectbox("Selecione o lançamento:", opcoes)
            
            nf_input = st.text_input("Vincular Número da NF (opcional):")

            if st.button("Confirmar Baixa"):
                idx_orig = df_pendentes.index[opcoes.index(selecionado)]
                tipo_item = df_fluxo.at[idx_orig, 'TIPO']
                
                # Atualiza Status
                df_fluxo.at[idx_orig, 'STATUS'] = "RECEBIDO" if tipo_item == "ENTRADA" else "PAGO"
                
                # Atualiza NF se foi digitada
                if nf_input:
                    df_fluxo.at[idx_orig, 'NF'] = nf_input
                
                # Salva no Google Sheets
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo)
                st.success("Baixa realizada com sucesso!")
                st.rerun()
        else:
            st.info("Não há contas pendentes para baixar.")

    with tab_fixos:
        st.subheader("Lançar Gastos Fixos")
        st.write("Copia os itens da aba 'Gastos Fixos' para o seu fluxo como PENDENTE.")
        mes_ref = st.selectbox("Referente ao mês de:", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
        
        if st.button("Executar Lançamentos Mensais"):
            novos_gastos = []
            for _, gasto in df_gastos_fixos.iterrows():
                novos_gastos.append({
                    "DATA": datetime.now().strftime("%d/%m/%Y"),
                    "TIPO": "SAIDA",
                    "CLIENTE": f"{gasto['ITEM']} ({mes_ref})",
                    "VALOR": gasto['VALOR'],
                    "PARCELA": "1/1",
                    "STATUS": "PENDENTE",
                    "NF": ""
                })
            
            if novos_gastos:
                df_novo_fluxo = pd.concat([df_fluxo, pd.DataFrame(novos_gastos)], ignore_index=True)
                conn.update(worksheet="Fluxo de Caixa", data=df_novo_fluxo)
                st.success(f"Gastos de {mes_ref} lançados com sucesso!")
                st.rerun()

except Exception as e:
    st.error(f"Erro ao processar o Financeiro: {e}")