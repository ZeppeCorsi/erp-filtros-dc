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
    
   # --- 5. ABAS REFORMULADAS ---
    t1, t2, t3, t4 = st.tabs(["📄 Extrato Geral", "📅 Fluxo Futuro", "✅ Baixa / NF", "⚙️ Lançar Gasto Fixo"])

    with t1:
        st.subheader("Histórico Completo")
        # Mostramos a coluna TIPO para você saber o que é Entrada e o que é Saída
        st.dataframe(df_fluxo[['DATA', 'TIPO', 'CLIENTE', 'VALOR', 'STATUS', 'NF']].sort_index(ascending=False), use_container_width=True)

    with t2:
        st.subheader("Previsão de Entradas e Saídas")
        data_alvo = st.date_input("Ver movimentações até:", datetime.now())
        data_alvo_str = data_alvo.strftime("%d/%m/%Y")
        
        # Filtra apenas o que é PENDENTE e bate com a data
        previsao = df_fluxo[(df_fluxo['STATUS'] == 'PENDENTE')]
        st.write(f"Itens pendentes aguardados:")
        st.dataframe(previsao[['DATA', 'TIPO', 'CLIENTE', 'VALOR']], use_container_width=True)

    with t3:
        st.subheader("Confirmar Recebimento/Pagamento")
        df_pend = df_fluxo[df_fluxo['STATUS'] == 'PENDENTE'].copy()
        if not df_pend.empty:
            opcoes = df_pend.apply(lambda x: f"{x['DATA']} | {x['CLIENTE']} (R$ {x['VALOR']:.2f})", axis=1).tolist()
            escolha = st.selectbox("Selecione para dar baixa:", opcoes)
            nova_nf = st.text_input("Vincular NF:")
            
            if st.button("Confirmar Baixa"):
                idx = df_pend.index[opcoes.index(escolha)]
                tipo = df_fluxo.at[idx, 'TIPO']
                df_fluxo.at[idx, 'STATUS'] = "RECEBIDO" if tipo == "ENTRADA" else "PAGO"
                if nova_nf: df_fluxo.at[idx, 'NF'] = nova_nf
                
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo)
                st.success("Status atualizado na planilha!")
                st.rerun()
        else:
            st.info("Nada pendente para baixar.")

    with t4:
        st.subheader("Lançamento Individual de Gasto Fixo")
        st.write("Escolha um item da sua lista de custos para enviar ao Fluxo:")
        
        # Lista os gastos da sua aba 'Gastos Fixos' (Coluna DETALHE da image_aacce1)
        lista_gastos = df_gastos_fixos['DETALHE'].tolist()
        gasto_selecionado = st.selectbox("Qual conta deseja lançar?", lista_gastos)
        
        # Busca o valor automático desse gasto
        valor_sugerido = df_gastos_fixos[df_gastos_fixos['DETALHE'] == gasto_selecionado]['VALOR'].values[0]
        valor_final = st.number_input("Confirme o Valor (R$):", value=float(valor_sugerido))
        data_lancamento = st.date_input("Data do Vencimento:", datetime.now())
        
        if st.button("Lançar no Fluxo de Caixa"):
            novo_item = pd.DataFrame([{
                "DATA": data_lancamento.strftime("%d/%m/%Y"),
                "TIPO": "SAIDA",
                "CLIENTE": gasto_selecionado,
                "VALOR": valor_final,
                "STATUS": "PENDENTE",
                "NF": ""
            }])
            
            df_atualizado = pd.concat([df_fluxo, novo_item], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_atualizado)
            st.success(f"{gasto_selecionado} adicionado ao Fluxo como pendente!")
            st.rerun()

except Exception as e:
    st.error(f"Erro: {e}")
