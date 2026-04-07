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
        # Remove colunas e linhas totalmente vazias
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def aba_gestao_locacao():
    st.subheader("📑 Gestão de Locação - Filtros DC")
    
    df_clientes = carregar_dados("Clientes")
    df_produtos = carregar_dados("Produtos")
    
    with st.form("nova_locacao", clear_on_submit=True):
        st.markdown("### Registrar Contrato e Provisionar 12 Meses")
        # ... (seu código de inputs aqui: data_ini, cliente, produto, valor_mensal)
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
                if not filtro.empty: custo_total = float(filtro.values[0])
            st.info(f"Custo de Aquisição: R$ {custo_total:,.2f}")

        submit = st.form_submit_button("Gerar Locação e Lançamentos")

        if submit:
            try:
                # --- LÓGICA DE GRAVAÇÃO (Já funcionando conforme seu feedback) ---
                df_loc_antigo = conn.read(worksheet="Locacao").dropna(how='all')
                nova_loc = pd.DataFrame([{"DATA_INICIO": data_ini.strftime("%d/%m/%Y"), "CLIENTE": cliente, "EQUIPAMENTO": produto, "VALOR_MENSAL": valor_mensal, "CUSTO_ORIGINAL": custo_total}])
                conn.update(worksheet="Locacao", data=pd.concat([df_loc_antigo, nova_loc], ignore_index=True))

                df_fluxo_antigo = conn.read(worksheet="Fluxo de Caixa").dropna(how='all')
                df_vendas_antigo = conn.read(worksheet="Vendas").dropna(how='all')
                
                novas_vendas, novos_fluxos = [], []
                for i in range(1, 13):
                    venc = (data_ini + relativedelta(months=i-1)).replace(day=5)
                    dt_s = venc.strftime("%d/%m/%Y")
                    novos_fluxos.append({"DATA": dt_s, "TIPO": "ENTRADA", "DESCRICAO": f"LOCACAO - {produto}", "VALOR": valor_mensal, "PARCELA": f"{i}/12", "STATUS": "PREVISTO", "CLIENTE": cliente, "NF": "LOC"})
                    novas_vendas.append({"NF": "LOC", "DATA": dt_s, "CLIENTE": cliente, "PRODUTO": produto, "CFOPS": "LOC", "TOTAL": valor_mensal, "COMPRAS": 0, "FORMA DE PAGAMENTO": "BOLETO/LOC", "QTD": 1, "VALOR UNIT": valor_mensal, "VENDEDOR": "SISTEMA", "OBS": f"Parc {i}/12", "CUSTO": 0, "MARGEM": valor_mensal})
                
                conn.update(worksheet="Fluxo de Caixa", data=pd.concat([df_fluxo_antigo, pd.DataFrame(novos_fluxos)], ignore_index=True).iloc[:, :8])
                conn.update(worksheet="Vendas", data=pd.concat([df_vendas_antigo, pd.DataFrame(novas_vendas)], ignore_index=True).iloc[:, :14])

                st.success("✅ Tudo gravado com sucesso!")
                st.rerun() # Força a página a recarregar para atualizar a tabela abaixo
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

    # --- TABELA DE CONTROLE (FORA DO IF SUBMIT PARA APARECER SEMPRE) ---
    st.markdown("---")
    st.subheader("📅 Próximos Reajustes (12ª Parcela)")
    
    # Lemos a aba Locacao novamente para garantir dados frescos
    df_exibir = carregar_dados("Locacao")
    
    if not df_exibir.empty:
        # Padroniza nomes de colunas para evitar o KeyError
        df_exibir.columns = [str(c).strip().upper() for c in df_exibir.columns]
        
        if 'DATA_INICIO' in df_exibir.columns:
            try:
                # Converter datas com segurança
                df_exibir['DATA_DT'] = pd.to_datetime(df_exibir['DATA_INICIO'], dayfirst=True, errors='coerce')
                df_exibir = df_exibir.dropna(subset=['DATA_DT'])
                
                # Calcular 12ª parcela e dias restantes
                df_exibir['DATA 12ª PARCELA'] = df_exibir['DATA_DT'].apply(lambda x: (x + relativedelta(months=11)).replace(day=5))
                df_exibir['DIAS PARA REAJUSTE'] = (df_exibir['DATA 12ª PARCELA'] - pd.Timestamp(date.today())).dt.days
                
                # Criar DataFrame amigável para exibição
                df_final = df_exibir.copy()
                df_final['DATA 12ª PARCELA'] = df_final['DATA 12ª PARCELA'].dt.strftime('%d/%m/%Y')
                
                # Selecionar e renomear colunas
                colunas_vistas = ['CLIENTE', 'EQUIPAMENTO', 'VALOR_MENSAL', 'DATA 12ª PARCELA', 'DIAS PARA REAJUSTE']
                df_final = df_final[colunas_vistas].rename(columns={'EQUIPAMENTO': 'PRODUTO', 'VALOR_MENSAL': 'VALOR (R$)'})

                # Exibir com cor de alerta
                st.dataframe(
                    df_final.style.applymap(lambda x: 'color: red; font-weight: bold' if isinstance(x, int) and x <= 30 else 'color: black', subset=['DIAS PARA REAJUSTE']),
                    use_container_width=True
                )
            except Exception as e:
                st.warning(f"Erro ao processar cronograma: {e}")
        else:
            st.warning(f"Coluna 'DATA_INICIO' não encontrada. Colunas disponíveis: {list(df_exibir.columns)}")
    else:
        st.info("Nenhuma locação encontrada para monitoramento.")