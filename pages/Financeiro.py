import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA PÁGINA (Sempre o primeiro do Streamlit)
st.set_page_config(page_title="Financeiro | Filtros DC", layout="wide")

# 2. SEGURANÇA (O Porteiro)
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Por favor, faça o login na página principal.")
    st.stop() # Interrompe tudo que vem abaixo

# 3. CONFIGURAÇÕES DE CONEXÃO
ID_PLANILHA = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"

# Dica: Como vamos usar várias abas (Fluxo de Caixa, Gastos Fixos), 
# é melhor criar a URL dentro da função ou carregar via conn.read()
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# 4. FUNÇÕES DE APOIO (Limpeza, Carregamento, etc.)
def limpar_para_pdf(texto):
    if not texto: return ""
    import unicodedata
    t = str(texto).replace("R$", "RS").replace("R $", "RS")
    nfkd = unicodedata.normalize('NFKD', t)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).encode('ascii', 'ignore').decode('ascii')

def aba_financeira(conn):
    st.title("🏦 Controle Financeiro e Extrato")

    # 1. CARREGAMENTO DOS DADOS
    # Lendo as duas abas necessárias
    df_fluxo = conn.read(worksheet="Fluxo de Caixa")
    df_gastos_fixos = conn.read(worksheet="Gastos Fixos")
    
    # Tratamento de valores numéricos para não dar erro de soma
    df_fluxo['VALOR'] = pd.to_numeric(df_fluxo['VALOR'], errors='coerce').fillna(0)
    df_gastos_fixos['VALOR'] = pd.to_numeric(df_gastos_fixos['VALOR'], errors='coerce').fillna(0)

    # 2. DASHBOARD DE SALDO (O seu "Extrato Real")
    # Saldo = Tudo que é ENTRADA/RECEBIDO menos tudo que é SAIDA/PAGO
    entradas = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'RECEBIDO')]['VALOR'].sum()
    saidas = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PAGO')]['VALOR'].sum()
    saldo_real = entradas - saidas

    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo em Conta (Conciliado)", f"R$ {saldo_real:,.2f}")
    
    pendente_rec = df_fluxo[(df_fluxo['TIPO'] == 'ENTRADA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    col2.metric("A Receber (Previsão)", f"R$ {pendente_rec:,.2f}", delta_color="normal")
    
    pendente_pag = df_fluxo[(df_fluxo['TIPO'] == 'SAIDA') & (df_fluxo['STATUS'] == 'PENDENTE')]['VALOR'].sum()
    col3.metric("Contas a Pagar", f"R$ {pendente_pag:,.2f}", delta=f"-{pendente_pag:,.2f}", delta_color="inverse")

    st.divider()

    # 3. AUTOMAÇÃO DE GASTOS FIXOS
    with st.expander("⚙️ Lançar Gastos Fixos do Mês"):
        st.write("Isso vai copiar os gastos da aba 'Gastos Fixos' para o seu 'Fluxo de Caixa'.")
        mes_referencia = st.selectbox("Selecione o Mês", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
        
        if st.button("Gerar Lançamentos do Mês"):
            novos_lancamentos = []
            for _, gasto in df_gastos_fixos.iterrows():
                novo_item = {
                    "DATA": datetime.now().strftime("%d/%m/%Y"),
                    "TIPO": "SAIDA",
                    "CLIENTE": f"{gasto['ITEM']} - {mes_referencia}", # Ex: Aluguel - Março
                    "VALOR": gasto['VALOR'],
                    "PARCELA": "1/1",
                    "STATUS": "PENDENTE"
                }
                novos_lancamentos.append(novo_item)
            
            # Código para salvar no Google Sheets (ajuste o nome da função de salvar se necessário)
            df_atualizado = pd.concat([df_fluxo, pd.DataFrame(novos_lancamentos)], ignore_index=True)
            conn.update(worksheet="Fluxo de Caixa", data=df_atualizado)
            st.success(f"Gastos de {mes_referencia} lançados como PENDENTES!")
            st.rerun()

    # 4. SISTEMA DE BAIXA (CONCILIAÇÃO)
    st.subheader("✅ Dar Baixa em Pagamentos e Recebimentos")
    
    df_pendentes = df_fluxo[df_fluxo['STATUS'] == 'PENDENTE']
    
    if not df_pendentes.empty:
        # Criar uma lista para o selectbox
        lista_pendentes = df_pendentes.apply(lambda x: f"{x['CLIENTE']} | R$ {x['VALOR']:.2f} ({x['TIPO']})", axis=1).tolist()
        selecionado = st.selectbox("Escolha a conta que você pagou ou recebeu:", lista_pendentes)
        
        if st.button("Confirmar Baixa no Sistema"):
            # Acha o índice real na planilha
            indice_original = df_pendentes.index[lista_pendentes.index(selecionado)]
            
            # Se for entrada vira RECEBIDO, se for saída vira PAGO
            status_novo = "RECEBIDO" if df_fluxo.at[indice_original, 'TIPO'] == "ENTRADA" else "PAGO"
            
            # Atualiza o DataFrame e salva
            df_fluxo.at[indice_original, 'STATUS'] = status_novo
            conn.update(worksheet="Fluxo de Caixa", data=df_fluxo)
            
            st.success(f"Baixa realizada! {selecionado} agora consta como {status_novo}.")
            st.rerun()
    else:
        st.info("Não há lançamentos pendentes.")

    # 5. VISUALIZAÇÃO DO FLUXO (O EXTRATO)
    st.subheader("📄 Extrato Detalhado")
    # Inverter o DF para mostrar o mais recente no topo
    st.dataframe(df_fluxo.sort_index(ascending=False), use_container_width=True)