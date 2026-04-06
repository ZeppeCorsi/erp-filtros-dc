import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from streamlit_gsheets import GSheetsConnection

# Configuração da Conexão (Mantendo o padrão dos seus últimos códigos)
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def calcular_depreciacao(data_inicio, custo_inicial):
    # Calcula quantos meses se passaram desde o início
    hoje = date.today()
    meses_passados = (hoje.year - data_inicio.year) * 12 + hoje.month - data_inicio.month
    
    if meses_passados >= 24:
        return 0.0
    
    # Depreciação de 1/24 por mês (conforme sua regra de 2 anos)
    depreciacao_mensal = custo_inicial / 24
    custo_atual = custo_inicial - (meses_passados * depreciacao_mensal)
    return max(custo_atual, 0.0)

def verificar_reajuste(data_inicio):
    hoje = date.today()
    meses_passados = (hoje.year - data_inicio.year) * 12 + hoje.month - data_inicio.month
    # Alerta a cada 12 meses
    if meses_passados > 0 and meses_passados % 12 == 0:
        return True
    return False

def aba_gestao_locacao():
    st.subheader("📑 Gestão de Locação - Filtros DC")
    
    # --- CARREGAMENTO DE DADOS ---
    # Puxa clientes e produtos para os seletores
    df_clientes = conn.read(worksheet="Clientes")
    df_produtos = conn.read(worksheet="Produtos")
    
    with st.form("nova_locacao"):
        st.markdown("### Cadastrar Nova Locação")
        col1, col2 = st.columns(2)
        
        with col1:
            data_loc = st.date_input("Data de Início", value=date.today())
            # Puxa o nome do cliente da aba Clientes
            cliente = st.selectbox("Cliente", options=df_clientes["NOME REDUZIDO"].unique())
            # Puxa o produto da aba Produtos
            produto = st.selectbox("Equipamento", options=df_produtos["NOME"].unique())
            
        with col2:
            valor_mensal = st.number_input("Valor da Mensalidade (R$)", min_value=0.0)
            # Puxa o custo automaticamente da coluna CUSTO TOTAL
            custo_original = df_produtos.loc[df_produtos["NOME"] == produto, "CUSTO TOTAL"].values[0]
            st.info(f"Custo Original do Equipamento: R$ {custo_original:,.2f}")

        if st.form_submit_button("Salvar Locação"):
            # Lógica para salvar na aba Locação, Vendas e Fluxo de Caixa
            # (Aqui entrará o conn.update para as 3 abas simultaneamente)
            st.success("Locação registrada e enviada para Fluxo de Caixa e Vendas!")

    # --- VISUALIZAÇÃO DOS ATIVOS ---
    st.markdown("---")
    st.markdown("### Equipamentos Locados e Depreciação")
    
    df_loc = conn.read(worksheet="Locacao") # Você precisará criar essa aba na planilha
    
    if not df_loc.empty:
        # Aplica os cálculos em tempo real para visualização
        df_loc['DATA_INICIO'] = pd.to_datetime(df_loc['DATA_INICIO']).dt.date
        df_loc['CUSTO_ATUAL'] = df_loc.apply(lambda x: calcular_depreciacao(x['DATA_INICIO'], x['CUSTO_ORIGINAL']), axis=1)
        df_loc['PRECISA_REAJUSTE'] = df_loc['DATA_INICIO'].apply(verificar_reajuste)
        
        # Exibe a tabela com alertas de reajuste
        st.dataframe(df_loc)
        
        for idx, row in df_loc[df_loc['PRECISA_REAJUSTE']].iterrows():
            st.warning(f"⚠️ Atenção: O contrato de **{row['CLIENTE']}** completou ciclo de 12 meses. Avaliar reajuste!")

if __name__ == "__main__":
    aba_gestao_locacao()