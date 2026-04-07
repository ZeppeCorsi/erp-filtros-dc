import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from streamlit_gsheets import GSheetsConnection

# 1. CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def carregar_dados_limpos(aba):
    try:
        # Força o refresh (ttl=0)
        df = conn.read(worksheet=aba, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame()
        # Limpeza agressiva de espaços e linhas vazias
        df = df.dropna(how='all').reset_index(drop=True)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def aba_gestao_locacao():
    st.title("🚀 Painel de Locações - Filtros DC")
    
    # Carregamento de Tabelas de Apoio
    df_cli = carregar_dados_limpos("Clientes")
    df_prod = carregar_dados_limpos("Produtos")
    
    # --- SEÇÃO 1: FORMULÁRIO DE CADASTRO ---
    with st.expander("➕ Cadastrar Nova Locação (12 Meses)", expanded=True):
        with st.form("form_locacao", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                data_ini = st.date_input("Data de Início", value=date.today())
                clientes = sorted(df_cli["NOME REDUZIDO"].unique()) if not df_cli.empty else ["Nenhum"]
                cliente_sel = st.selectbox("Selecione o Cliente", clientes)
                
                produtos = sorted(df_prod["NOME"].unique()) if not df_prod.empty else ["Nenhum"]
                produto_sel = st.selectbox("Equipamento", produtos)

            with c2:
                vlr_mensal = st.number_input("Mensalidade (R$)", min_value=0.0, step=50.0)
                # Busca custo automático
                custo = 0.0
                if not df_prod.empty and produto_sel != "Nenhum":
                    res = df_prod.loc[df_prod["NOME"] == produto_sel, "CUSTO TOTAL"]
                    if not res.empty: custo = float(res.values[0])
                st.metric("Custo do Equipamento", f"R$ {custo:,.2f}")

            if st.form_submit_button("✅ Finalizar e Gerar 12 Parcelas"):
                try:
                    # --- GRAVAÇÃO EM LOTE ---
                    # 1. Registro em 'Locacao'
                    df_l_old = conn.read(worksheet="Locacao").dropna(how='all')
                    n_l = pd.DataFrame([{"DATA_INICIO": data_ini.strftime("%d/%m/%Y"), "CLIENTE": cliente_sel, 
                                         "EQUIPAMENTO": produto_sel, "VALOR_MENSAL": vlr_mensal, "CUSTO_ORIGINAL": custo}])
                    conn.update(worksheet="Locacao", data=pd.concat([df_l_old, n_l], ignore_index=True))

                    # 2. Gerar 12 meses (Fluxo e Vendas)
                    df_f_old = conn.read(worksheet="Fluxo de Caixa").dropna(how='all')
                    df_v_old = conn.read(worksheet="Vendas").dropna(how='all')
                    
                    l_f, l_v = [], []
                    for i in range(1, 13):
                        venc = (data_ini + relativedelta(months=i-1)).replace(day=5)
                        v_str = venc.strftime("%d/%m/%Y")
                        
                        l_f.append({"DATA": v_str, "TIPO": "ENTRADA", "DESCRICAO": f"MENSALIDADE {i}/12 - {produto_sel}",
                                    "VALOR": vlr_mensal, "PARCELA": f"{i}/12", "STATUS": "PREVISTO", "CLIENTE": cliente_sel, "NF": "LOC"})
                        
                        l_v.append(["LOC", v_str, cliente_sel, produto_sel, "LOC", vlr_mensal, 0, "BOLETO/LOC", 1, vlr_mensal, "SISTEMA", f"Parc {i}/12", 0, vlr_mensal])

                    # Update Final
                    conn.update(worksheet="Fluxo de Caixa", data=pd.concat([df_f_old, pd.DataFrame(l_f)], ignore_index=True).iloc[:, :8])
                    conn.update(worksheet="Vendas", data=pd.concat([df_v_old, pd.DataFrame(l_v, columns=df_v_old.columns[:14])], ignore_index=True).iloc[:, :14])
                    
                    st.success("Dados enviados! Atualizando painel...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro Crítico: {e}")

    # --- SEÇÃO 2: TABELA DE MONITORAMENTO (A QUE ESTAVA EM BRANCO) ---
    st.markdown("---")
    st.subheader("📊 Controle de Ativos e Reajustes")
    
    df_view = carregar_dados_limpos("Locacao")
    
    if not df_view.empty:
        try:
            # Tenta converter a primeira coluna que parecer uma data
            # (Caso 'DATA_INICIO' mude de nome por erro humano na planilha)
            col_data = "DATA_INICIO" if "DATA_INICIO" in df_view.columns else df_view.columns[0]
            
            df_view['DT_OBJ'] = pd.to_datetime(df_view[col_data], dayfirst=True, errors='coerce')
            df_view = df_view.dropna(subset=['DT_OBJ'])

            # Cálculos de 12ª Parcela
            df_view['VENC_12'] = df_view['DT_OBJ'].apply(lambda x: (x + relativedelta(months=11)).replace(day=5))
            df_view['DIAS'] = (df_view['VENC_12'] - pd.Timestamp(date.today())).dt.days
            
            # Formatação de Exibição
            df_final = df_view.copy()
            df_final['12ª PARCELA'] = df_final['VENC_12'].dt.strftime('%d/%m/%Y')
            
            # Filtro de Colunas Úteis
            cols_ok = [c for c in ['CLIENTE', 'EQUIPAMENTO', 'VALOR_MENSAL', '12ª PARCELA', 'DIAS'] if c in df_final.columns]
            
            # Estilização
            def colorir_vencimento(val):
                if isinstance(val, int) and val <= 30: return 'background-color: #ffcccc; color: red; font-weight: bold'
                return ''

            st.dataframe(
                df_final[cols_ok].style.applymap(colorir_vencimento, subset=['DIAS'] if 'DIAS' in cols_ok else []),
                use_container_width=True,
                hide_index=True
            )
            
            st.info("💡 Contratos em **vermelho** vencem o ciclo de 12 meses em menos de 30 dias.")

        except Exception as e:
            st.warning