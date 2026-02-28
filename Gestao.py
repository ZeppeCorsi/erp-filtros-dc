import streamlit as st

# Verificação de segurança: Se não estiver logado, para o código e avisa.
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Por favor, faça login na página Home.")
    st.stop()


import pandas as pd
import os
from datetime import datetime, date

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="ERP | Filtros DC", layout="wide")
st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)

NOME_ARQUIVO_VENDAS = "Vendas.xlsx"

def carregar_vendas():
    if os.path.exists(NOME_ARQUIVO_VENDAS):
        try:
            df = pd.read_excel(NOME_ARQUIVO_VENDAS, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            
            # TRATAMENTO DE DATA
            if 'Data' in df.columns:
                df['Data_DT'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            
            # --- LIMPEZA DE VALOR DEFINITIVA ---
            def limpar_dinheiro(valor):
                v = str(valor).strip().lower()
                if v in ['nan', 'none', '']: return 0.0
                v = "".join(c for c in v if c.isdigit() or c in [',', '.'])
                if ',' in v and '.' in v:
                    v = v.replace('.', '').replace(',', '.')
                elif ',' in v:
                    v = v.replace(',', '.')
                try:
                    return float(v)
                except:
                    return 0.0

            if 'faturamento' in df.columns:
                df['Valor_Num'] = df['faturamento'].apply(limpar_dinheiro)
            
            return df
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- INTERFACE ---
st.title("💰 Gestão de Vendas - Filtros DC")
df_vendas = carregar_vendas()
tab_estudo, tab_incluir = st.tabs(["📊 Estudo de Vendas", "➕ Incluir Nova Venda"])

with tab_estudo:
    if not df_vendas.empty:
        # 1. Calendário e Filtros
        st.subheader("📅 Período e Filtros")
        c1, c2 = st.columns(2)
        with c1: dt_ini = st.date_input("Início:", value=date(2021, 5, 1), format="DD/MM/YYYY")
        with c2: dt_fim = st.date_input("Fim:", value=date.today(), format="DD/MM/YYYY")

        df_periodo = df_vendas[(df_vendas['Data_DT'].dt.date >= dt_ini) & 
                               (df_vendas['Data_DT'].dt.date <= dt_fim)].copy()

        if not df_periodo.empty:
            # --- GRÁFICOS (RESTAURADOS) ---
            st.markdown("---")
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.subheader("🏆 Top 10 Clientes (Faturamento R$)")
                # Gráfico com valores corrigidos (Villa Borghese agora aparece certo)
                top_fat = df_periodo.groupby('Cliente')['Valor_Num'].sum().nlargest(10)
                st.bar_chart(top_fat)

            with col_graf2:
                st.subheader("🔄 Top 10 Clientes (Frequência)")
                # Gráfico de quantidade de pedidos no período
                top_freq = df_periodo['Cliente'].value_counts().nlargest(10)
                st.bar_chart(top_freq)

            # --- ANÁLISE POR CLIENTE ---
            st.markdown("---")
            st.subheader("🔍 Detalhar um Cliente")
            lista_cli = sorted(df_periodo['Cliente'].dropna().unique().tolist())
            cliente_sel = st.selectbox("Selecione para ver o extrato:", ["TODOS"] + lista_cli)
            
            df_final = df_periodo if cliente_sel == "TODOS" else df_periodo[df_periodo['Cliente'] == cliente_sel]

            # Métrica com valor real e formatado
            total_v = df_final['Valor_Num'].sum()
            st.metric(f"Total: {cliente_sel}", f"R$ {total_v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

            # TABELA FORMATADA
            df_view = df_final[['NF', 'Data_DT', 'Cliente', 'Produto', 'Valor_Num', 'Forma de pagamento']].copy()
            df_view['Data_DT'] = df_view['Data_DT'].dt.strftime('%d/%m/%Y')
            df_view['Valor_Num'] = df_view['Valor_Num'].apply(lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            df_view = df_view.rename(columns={'Data_DT': 'Data', 'Valor_Num': 'faturamento'})

            st.dataframe(df_view, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum dado encontrado para as datas selecionadas.")
    else:
        st.info("Planilha Vendas.xlsx não encontrada.")

with tab_incluir:
    st.subheader("Lançar Nova Venda")
    with st.form("form_venda", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            f_nf = st.text_input("NF")
            f_data = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
            f_cli = st.text_input("Cliente")
            f_prod = st.text_input("Produto")
        with c2:
            f_cfop = st.selectbox("CFOPs", ["serviço", "venda", "revenda"])
            f_fat = st.text_input("Faturamento (R$)")
            f_comp = st.text_input("Compras")
            f_pag = st.text_input("Forma de Pagamento")

        if st.form_submit_button("Registrar na Planilha"):
            try:
                nova = {'NF': f_nf, 'Data': f_data.strftime("%d/%m/%Y"), 'Cliente': f_cli.upper(), 
                        'Produto': f_prod.upper(), 'CFOPs': f_cfop, 'faturamento': f_fat, 
                        'compras': f_comp, 'Forma de pagamento': f_pag}
                pd.concat([df_vendas.drop(columns=['Data_DT', 'Valor_Num'], errors='ignore'), 
                           pd.DataFrame([nova])], ignore_index=True).to_excel(NOME_ARQUIVO_VENDAS, index=False)
                st.success("Venda salva com sucesso!"); st.rerun()
            except: st.error("Feche o Excel Vendas.xlsx!")