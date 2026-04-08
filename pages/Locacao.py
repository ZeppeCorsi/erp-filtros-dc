import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def carregar_dados(aba):
    try:
        df = conn.read(worksheet=aba)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def aba_gestao_locacao():
    st.subheader("📑 Gestão de Locação - Filtros DC")
    
    # Carregando dados auxiliares
    df_clientes = conn.read(worksheet="Clientes", ttl=0)
    df_produtos = conn.read(worksheet="Produtos", ttl=0)
    
    with st.form("nova_locacao", clear_on_submit=True):
        st.markdown("### Registrar Contrato Personalizado")
        col1, col2 = st.columns(2)
        
        with col1:
            data_ini = st.date_input("Início da Locação", value=date.today())
            lista_cli = sorted(df_clientes["NOME REDUZIDO"].dropna().unique().tolist()) if df_clientes is not None else ["Vazio"]
            cliente = st.selectbox("Cliente", options=lista_cli)
            
            lista_prod = sorted(df_produtos["NOME"].dropna().unique().tolist()) if df_produtos is not None else ["Vazio"]
            produto = st.selectbox("Equipamento (Filtro)", options=lista_prod)
            
        with col2:
            valor_mensal = st.number_input("Valor Mensal (R$)", min_value=0.0, format="%.2f")
            qtd_parcelas_restantes = st.number_input("Quantas parcelas lançar no financeiro?", min_value=1, max_value=48, value=12)
            
        if st.form_submit_button("Gerar Locação e Lançamentos"):
            try:
                # 1. LER DADOS ATUAIS (Garante que as variáveis existem antes de usar)
                df_loc_atual = conn.read(worksheet="Locacao", ttl=0).dropna(how='all')
                df_fluxo_antigo = conn.read(worksheet="Fluxo de Caixa", ttl=0).dropna(how='all')
                df_vendas_antigo = conn.read(worksheet="Vendas", ttl=0).dropna(how='all')

                # 2. Gravação na aba Locacao
                nova_linha_loc = pd.DataFrame([{
                    "DATA_INICIO": data_ini.strftime("%d/%m/%Y"),
                    "CLIENTE": cliente,
                    "EQUIPAMENTO": produto,
                    "VALOR_MENSAL": valor_mensal
                }])
                conn.update(worksheet="Locacao", data=pd.concat([df_loc_atual, nova_linha_loc], ignore_index=True))

                # 3. Gerar as parcelas como PENDENTE
                novas_vendas = []
                novos_fluxos = []

                for i in range(1, int(qtd_parcelas_restantes) + 1):
                    vencimento = (data_ini + relativedelta(months=i-1)).replace(day=5)
                    dt_str = vencimento.strftime("%d/%m/%Y")
                    
                    novos_fluxos.append({
                        "DATA": dt_str, "TIPO": "ENTRADA", "DESCRICAO": f"LOCACAO - {produto}",
                        "VALOR": valor_mensal, "PARCELA": f"{i}/{qtd_parcelas_restantes}", 
                        "STATUS": "PENDENTE", "CLIENTE": cliente, "NF": "LOC"
                    })

                    novas_vendas.append({
                        "NF": "LOC", "DATA": dt_str, "CLIENTE": cliente, "PRODUTO": produto,
                        "CFOPS": "LOC", "TOTAL": valor_mensal, "COMPRAS": 0,
                        "FORMA DE PAGAMENTO": "BOLETO/LOC", "QTD": 1, "VALOR UNIT": valor_mensal,
                        "VENDEDOR": "SISTEMA", "OBS": f"Parc {i}/{qtd_parcelas_restantes}", 
                        "CUSTO": 0, "MARGEM": valor_mensal
                    })
                
                # 4. SALVAMENTO NO SHEETS
                if novos_fluxos:
                    df_fluxo_final = pd.concat([df_fluxo_antigo, pd.DataFrame(novos_fluxos)], ignore_index=True)
                    conn.update(worksheet="Fluxo de Caixa", data=df_fluxo_final.iloc[:, :8])
                
                if novas_vendas:
                    df_vendas_final = pd.concat([df_vendas_antigo, pd.DataFrame(novas_vendas)], ignore_index=True)
                    conn.update(worksheet="Vendas", data=df_vendas_final.iloc[:, :14])

                st.success(f"✅ Sucesso! {qtd_parcelas_restantes} parcelas geradas como PENDENTE.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao processar: {e}")

    # 5. VISUALIZAÇÃO (Fora do Form)
    st.markdown("---")
    df_controle = conn.read(worksheet="Locacao", ttl=0)
    if df_controle is not None and not df_controle.empty:
        st.write("### 📋 Contratos Registrados")
        # Ajuste de .applymap para .map aqui se houver erro de tabela
        st.dataframe(df_controle, use_container_width=True, hide_index=True)

# Chamada da função
if __name__ == "__main__":
    aba_gestao_locacao()