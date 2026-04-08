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
    
    df_clientes = carregar_dados("Clientes")
    df_produtos = carregar_dados("Produtos")
    
    # --- BLOCO 1: FORMULÁRIO DE CADASTRO ---
    with st.form("nova_locacao", clear_on_submit=True):
        st.markdown("### Registrar Contrato e Provisionar 12 Meses")
        col1, col2 = st.columns(2)
        
        with col1:
            data_ini = st.date_input("Início da Locação", value=date.today())
            lista_cli = sorted(df_clientes["NOME REDUZIDO"].dropna().unique().tolist()) if not df_clientes.empty else ["Vazio"]
            cliente = st.selectbox("Cliente", options=lista_cli)
            
            lista_prod = sorted(df_produtos["NOME"].dropna().unique().tolist()) if not df_produtos.empty else ["Vazio"]
            produto = st.selectbox("Equipamento (Filtro)", options=lista_prod)
            
        with col2:
            valor_mensal = st.number_input("Valor Mensal (R$)", min_value=0.0, format="%.2f")
            custo_total = 0.0
            if not df_produtos.empty and produto != "Vazio":
                filtro = df_produtos.loc[df_produtos["NOME"] == produto, "CUSTO TOTAL"]
                if not filtro.empty:
                    custo_total = float(filtro.values[0])
            st.info(f"Custo de Aquisição: R$ {custo_total:,.2f}")

        # Botão de enviar
        submit = st.form_submit_button("Gerar Locação e Lançamentos")

        if submit:
            try:
                # 1. Preparar dados para a aba Locacao
                df_loc_atual = conn.read(worksheet="Locacao")
                nova_linha_loc = pd.DataFrame([{
                    "DATA_INICIO": data_ini.strftime("%d/%m/%Y"),
                    "CLIENTE": cliente,
                    "EQUIPAMENTO": produto,
                    "VALOR_MENSAL": valor_mensal,
                    "CUSTO_ORIGINAL": custo_total
                }])
                df_loc_final = pd.concat([df_loc_atual, nova_linha_loc], ignore_index=True)
                conn.update(worksheet="Locacao", data=df_loc_final)

                # 2. Preparar as 12 parcelas
                df_fluxo_atual = conn.read(worksheet="Fluxo de Caixa")
                df_vendas_atual = conn.read(worksheet="Vendas")
                
                novas_vendas = []
                novos_fluxos = []
                # Definimos a data de corte: 01 de Abril de 2026
                data_corte = date(2026, 4, 1)

                for i in range(1, 13):
                    vencimento = (data_ini + relativedelta(months=i-1)).replace(day=5)
                    dt_str = vencimento.strftime("%d/%m/%Y")
                    # SÓ PROCESSA SE O VENCIMENTO FOR A PARTIR DE ABRIL/2026
                    if vencimento >= data_corte:
                        dt_str = vencimento.strftime("%d/%m/%Y")
                    
                    novos_fluxos.append({
                        "DATA": dt_str, "TIPO": "ENTRADA", "DESCRICAO": f"LOCACAO - {produto}",
                        "VALOR": valor_mensal, "PARCELA": f"{i}/12", "STATUS": "PREVISTO", 
                        "CLIENTE": cliente, "NF": "LOC"
                    })

                    novas_vendas.append({
                        "NF": "LOC", "DATA": dt_str, "CLIENTE": cliente, "PRODUTO": produto,
                        "CFOPS": "LOC", "TOTAL": valor_mensal, "COMPRAS": 0,
                        "FORMA DE PAGAMENTO": "BOLETO/LOC", "QTD": 1, "VALOR UNIT": valor_mensal,
                        "VENDEDOR": "SISTEMA", "OBS": f"Parc {i}/12", "CUSTO": 0, "MARGEM": valor_mensal
                    })
                
                df_fluxo_final = pd.concat([df_fluxo_atual, pd.DataFrame(novos_fluxos)], ignore_index=True)
                df_vendas_final = pd.concat([df_vendas_atual, pd.DataFrame(novas_vendas)], ignore_index=True)
                
                conn.update(worksheet="Fluxo de Caixa", data=df_fluxo_final)
                conn.update(worksheet="Vendas", data=df_vendas_final)

                st.success("✅ Tudo pronto! Locação e 12 parcelas gravadas com sucesso.")
                st.balloons()
                st.rerun() # Força a atualização da tela para mostrar o dado novo na lista abaixo

            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

    # --- BLOCO 2: LISTA DE CONTROLE (FORA DO FORMULÁRIO) ---
    # Note que agora o st.markdown está alinhado com o "with st.form" lá de cima
    st.markdown("---")
    st.markdown("### 📅 Controle de Contratos (Vencimento da 12ª Parcela)")
    
    df_controle = carregar_dados("Locacao")
    
    if not df_controle.empty:
        # 1. Converter a coluna de data
        df_controle['DATA_INICIO'] = pd.to_datetime(df_controle['DATA_INICIO'], dayfirst=True)
        
        # 2. Calcular 12ª parcela
        df_controle['VENCIMENTO_12_PARC'] = df_controle['DATA_INICIO'].apply(
            lambda x: (x + relativedelta(months=11)).replace(day=5)
        )
        
        # 3. Dias restantes
        hoje = pd.Timestamp(date.today())
        df_controle['DIAS_RESTANTES'] = (df_controle['VENCIMENTO_12_PARC'] - hoje).dt.days
        
        # 4. Formatação
        df_display = df_controle.copy()
        df_display['DATA_INICIO'] = df_display['DATA_INICIO'].dt.strftime('%d/%m/%Y')
        df_display['VENCIMENTO_12_PARC'] = df_display['VENCIMENTO_12_PARC'].dt.strftime('%d/%m/%Y')
        
        df_display = df_display.rename(columns={
            'EQUIPAMENTO': 'PRODUTO',
            'VALOR_MENSAL': 'VALOR (R$)',
            'VENCIMENTO_12_PARC': 'DATA 12ª PARCELA',
            'DIAS_RESTANTES': 'DIAS PARA FIM'
        })

        def destacar_vencimento(val):
            return 'color: red' if val <= 30 else 'color: black'

        # Exibir a tabela na tela sempre que a aba carregar
        st.dataframe(
            df_display[['CLIENTE', 'PRODUTO', 'VALOR (R$)', 'DATA 12ª PARCELA', 'DIAS PARA FIM']]
            .style.map(destacar_vencimento, subset=['DIAS PARA FIM'])
        )
        st.caption("💡 Linhas em vermelho indicam contratos que vencem em menos de 30 dias.")
    else:
        st.info("Nenhuma locação registrada para exibir o cronograma.")

if __name__ == "__main__":
    aba_gestao_locacao()