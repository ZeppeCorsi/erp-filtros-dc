import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Financeiro | Filtros DC", layout="wide")

if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Faça o login na home.")
    st.stop()

conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- PROCESSAMENTO DE DADOS ---
try:
    df_fluxo_raw = conn.read(worksheet="Fluxo de Caixa", ttl=0)
    df_gastos_raw = conn.read(worksheet="Gastos Fixos", ttl=0)

    # Padronização de Colunas
    df_fluxo = df_fluxo_raw.copy()
    df_fluxo.columns = [str(c).strip().upper() for c in df_fluxo.columns]
    
    df_gastos_fixos = df_gastos_raw.copy()
    df_gastos_fixos.columns = [str(c).strip().upper() for c in df_gastos_fixos.columns]

    # Conversões e Tratamento de Erros
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
    df_fluxo['TIPO'] = df_fluxo['TIPO'].astype(str).str.strip().upper()
    df_fluxo['STATUS'] = df_fluxo['STATUS'].astype(str).str.strip().upper()
    
    # Datas e Ordenação Cronológica
    df_fluxo['DT_OBJ'] = pd.to_datetime(df_fluxo['DATA'], dayfirst=True, errors='coerce')
    df_fluxo = df_fluxo.dropna(subset=['DT_OBJ']).sort_values('DT_OBJ')
    df_fluxo['MES_REF'] = df_fluxo['DT_OBJ'].dt.strftime('%m/%Y')

    # --- CÁLCULO DE SALDO REAL (MATEMÁTICA CORRETA) ---
    ent_total = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    sai_total = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_atual_conta = ent_total - sai_total

    # --- INTERFACE ---
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    # Seletor de Mês (Estilo Extrato)
    meses_lista = ["Tudo"] + sorted(df_fluxo['MES_REF'].unique().tolist(), key=lambda x: datetime.strptime(x, '%m/%Y'))
    filtro_mes = st.selectbox("Período do Extrato:", meses_lista, index=len(meses_lista)-1)

    # Filtragem dos dados para exibição
    df_filtrado = df_fluxo if filtro_mes == "Tudo" else df_fluxo[df_fluxo['MES_REF'] == filtro_mes]

    # Métricas do Mês selecionado
    ent_mes = df_filtrado[(df_filtrado['TIPO'] == 'ENTRADA') & (df_filtrado['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    sai_mes = df_filtrado[(df_filtrado['TIPO'] == 'SAIDA') & (df_filtrado['STATUS'] == 'PAGO')]['VALOR'].sum()

    # Exibição
    m1, m2, m3 = st.columns(3)
    m1.metric("Saldo Real (Conta Hoje)", f"R$ {saldo_atual_conta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    m2.metric(f"Entradas ({filtro_mes})", f"R$ {ent_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    m3.metric(f"Saídas ({filtro_mes})", f"R$ {sai_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.divider()

    # --- ABAS ---
    t1, t2, t3, t4 = st.tabs(["📄 Extrato", "📅 Previsão", "✅ Baixa / NF", "⚙️ Lançar Fixo"])

    with t1:
        st.subheader(f"Extrato: {filtro_mes}")
        df_ver = df_filtrado[['DATA', 'TIPO', 'CLIENTE', 'VALOR', 'STATUS', 'NF']].copy()
        # Formatação Visual R$ 0.000,00
        df_ver['VALOR'] = df_ver['VALOR'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.dataframe(df_ver, use_container_width=True, hide_index=True)

    with t2:
        st.subheader("Contas Pendentes")
        df_pend = df_filtrado[df_filtrado['STATUS'] == 'PENDENTE'].copy()
        if not df_pend.empty:
            df_pend['VALOR'] = df_pend['VALOR'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.dataframe(df_pend[['DATA', 'TIPO', 'CLIENTE', 'VALOR']], use_container_width=True, hide_index=True)
        else:
            st.info("Nada pendente neste período.")

    with t3:
        st.subheader("Dar Baixa Individual")
        df_baixa = df_filtrado[df_filtrado['STATUS'] == 'PENDENTE'].copy()
        if not df_baixa.empty:
            opcoes = df_baixa.apply(lambda x: f"{x['DATA']} - {x['CLIENTE']} (R$ {x['VALOR']:.2f})", axis=1).tolist()
            selecionado = st.selectbox("Escolha o lançamento:", opcoes)
            nova_nf = st.text_input("Número da NF:")
            
            if st.button("Confirmar"):
                idx_original = df_baixa.index[opcoes.index(selecionado)]
                tipo_item = df_fluxo.at[idx_original, 'TIPO']
                df_fluxo.at[idx_original, 'STATUS'] = "RECEBIDO" if tipo_item == "ENTRADA" else "PAGO"
                if nova_nf: df_fluxo.at[idx_original, 'NF'] = nova_nf
                
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo.drop(columns=['DT_OBJ', 'MES_REF']))
                st.success("Baixa realizada!")
                st.rerun()

    with t4:
        st.subheader("Lançar Gasto Fixo Único")
        lista_fixos = df_gastos_fixos['DETALHE'].tolist()
        escolha_fixo = st.selectbox("Qual gasto fixo?", lista_fixos)
        v_sugerido = df_gastos_fixos[df_gastos_fixos['DETALHE'] == escolha_fixo]['VALOR'].values[0]
        
        c_v, c_d = st.columns(2)
        v_final = c_v.number_input("Valor:", value=float(v_sugerido))
        d_final = c_d.date_input("Vencimento:", datetime.now())
        
        if st.button("Lançar no Fluxo"):
            novo_df = pd.DataFrame([{
                "DATA": d_final.strftime("%d/%m/%Y"),
                "TIPO": "SAIDA",
                "CLIENTE": escolha_fixo,
                "VALOR": v_final,
                "STATUS": "PENDENTE",
                "NF": ""
            }])
            # Limpa as colunas de apoio antes de salvar
            df_salvar = pd.concat([df_fluxo.drop(columns=['DT_OBJ', 'MES_REF']), novo_df], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_salvar)
            st.success("Lançado!")
            st.rerun()

except Exception as e:
    st.error(f"Erro crítico: {e}")