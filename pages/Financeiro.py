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

# --- PROCESSAMENTO DE DADOS (VERSÃO BLINDADA) ---
# --- PROCESSAMENTO DE DADOS ---
try:
    df_fluxo_raw = conn.read(worksheet="Fluxo de Caixa", ttl=0)
    df_gastos_raw = conn.read(worksheet="Gastos Fixos", ttl=0)

    # 1. Limpeza Fluxo de Caixa
    df_fluxo = df_fluxo_raw.copy()
    df_fluxo.columns = [str(c).strip().upper() for c in df_fluxo.columns]
    
    # Garante que a coluna DESCRICAO existe na planilha
    if 'DESCRICAO' not in df_fluxo.columns:
        df_fluxo['DESCRICAO'] = ""

    # Tratamentos básicos
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
    df_fluxo['TIPO'] = df_fluxo['TIPO'].astype(str).str.upper().str.strip()
    df_fluxo['STATUS'] = df_fluxo['STATUS'].astype(str).str.upper().str.strip()
    
    # Datas e Meses
    df_fluxo['DT_OBJ'] = pd.to_datetime(df_fluxo['DATA'], dayfirst=True, errors='coerce')
    df_fluxo = df_fluxo.dropna(subset=['DT_OBJ']).sort_values('DT_OBJ')
    df_fluxo['MES_REF'] = df_fluxo['DT_OBJ'].dt.strftime('%m/%Y')

    # 2. Limpeza Gastos Fixos
    df_gastos_fixos = df_gastos_raw.copy()
    df_gastos_fixos.columns = [str(c).strip().upper() for c in df_gastos_fixos.columns]

    # --- MATEMÁTICA DO SALDO ---
    ent_total = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    sai_total = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_real = ent_total - sai_total

    # --- DASHBOARD ---
    st.title("🏦 Gestão Financeira - Filtros DC")
    
    meses_lista = ["Tudo"] + sorted(df_fluxo['MES_REF'].unique().tolist(), key=lambda x: datetime.strptime(x, '%m/%Y'))
    filtro_mes = st.selectbox("Período do Extrato:", meses_lista, index=len(meses_lista)-1)
    df_filtrado = df_fluxo if filtro_mes == "Tudo" else df_fluxo[df_fluxo['MES_REF'] == filtro_mes]

    m1, m2, m3 = st.columns(3)
    m1.metric("Saldo Real Hoje", f"R$ {saldo_real:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    ent_mes = df_filtrado[(df_filtrado['TIPO'] == 'ENTRADA') & (df_filtrado['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    sai_mes = df_filtrado[(df_filtrado['TIPO'] == 'SAIDA') & (df_filtrado['STATUS'] == 'PAGO')]['VALOR'].sum()
    
    m2.metric(f"Entradas ({filtro_mes})", f"R$ {ent_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    m3.metric(f"Saídas ({filtro_mes})", f"- R$ {sai_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")

    st.divider()

    # --- ABAS ---
    t1, t2, t3, t4 = st.tabs(["📄 Extrato", "📅 Pendências", "✅ Baixa / NF", "⚙️ Lançar Fixo"])

    with t1:
        st.subheader(f"Movimentações Detalhadas: {filtro_mes}")
        
        def formatar_v(linha):
            v = linha['VALOR']
            prefixo = "- " if linha['TIPO'] == 'SAIDA' else ""
            return f"{prefixo}R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        # Incluída a coluna DESCRICAO na visualização
        df_ver = df_filtrado[['DATA', 'TIPO', 'CLIENTE', 'DESCRICAO', 'VALOR', 'STATUS', 'NF']].copy()
        df_ver['VALOR'] = df_ver.apply(formatar_v, axis=1)
        st.dataframe(df_ver, use_container_width=True, hide_index=True)

    with t3:
        st.subheader("Dar Baixa")
        df_baixa = df_filtrado[df_filtrado['STATUS'] == 'PENDENTE'].copy()
        if not df_baixa.empty:
            # Mostra a descrição no seletor para facilitar a identificação
            opcoes = df_baixa.apply(lambda x: f"{x['DATA']} | {x['CLIENTE']} - {x['DESCRICAO']} (R$ {x['VALOR']:.2f})", axis=1).tolist()
            selecionado = st.selectbox("Selecione o item:", opcoes)
            nova_nf = st.text_input("Vincular NF:")
            
            if st.button("Confirmar Baixa"):
                idx = df_baixa.index[opcoes.index(selecionado)]
                tipo_item = df_fluxo.at[idx, 'TIPO']
                df_fluxo.at[idx, 'STATUS'] = "RECEBIDO" if tipo_item == "ENTRADA" else "PAGO"
                if nova_nf: df_fluxo.at[idx, 'NF'] = nova_nf
                
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo.drop(columns=['DT_OBJ', 'MES_REF']))
                st.success("Atualizado!")
                st.rerun()

    with t4:
        st.subheader("Lançar Gasto Fixo")
        item_fixo = st.selectbox("Escolha o custo:", df_gastos_fixos['DETALHE'].tolist())
        v_sugerido = df_gastos_fixos[df_gastos_fixos['DETALHE'] == item_fixo]['VALOR'].values[0]
        
        c_v, c_d = st.columns(2)
        v_f = c_v.number_input("Valor:", value=float(v_sugerido))
        d_f = c_d.date_input("Vencimento:", datetime.now())
        # Campo para o usuário preencher a descrição do gasto fixo
        desc_f = st.text_input("Descrição detalhada (ex: Ref. Janeiro):", value=f"Gasto Fixo - {item_fixo}")
        
        if st.button("Lançar no Fluxo"):
            novo = pd.DataFrame([{
                "DATA": d_f.strftime("%d/%m/%Y"),
                "TIPO": "SAIDA",
                "CLIENTE": item_fixo,
                "DESCRICAO": desc_f,
                "VALOR": v_f,
                "STATUS": "PENDENTE",
                "NF": ""
            }])
            df_salvar = pd.concat([df_fluxo.drop(columns=['DT_OBJ', 'MES_REF']), novo], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_salvar)
            st.success("Lançado com sucesso!")
            st.rerun()

except Exception as e:
    st.error(f"Erro: {e}")