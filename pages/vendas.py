# --- ABA VENDAS (BUSCANDO ORÇAMENTO) ---
st.title("💰 Registrar Venda (Efetivar Orçamento)")

# 1. BUSCA DO ORÇAMENTO PENDENTE
with st.container(border=True):
    st.subheader("🔍 Selecione o Orçamento para Venda")
    
    # Lemos a base de orçamentos e a de vendas (para saber o que já foi vendido)
    df_orc = conn.read(worksheet="Orcamentos", ttl=0).dropna(how='all')
    df_vendas_existentes = conn.read(worksheet="Vendas", ttl=0).dropna(how='all')
    
    if not df_orc.empty:
        # Criamos a lista de orçamentos disponíveis
        df_orc['REF'] = df_orc['DATA'] + " - " + df_orc['CLIENTE']
        lista_opcoes = sorted(df_orc['REF'].unique().tolist(), reverse=True)
        
        orc_venda = st.selectbox("Orçamentos Disponíveis:", [""] + lista_opcoes, help="Selecione o orçamento que o cliente aprovou")
        
        if orc_venda != "":
            data_o, cli_o = orc_venda.split(" - ", 1)
            
            # Filtramos os itens desse orçamento
            itens_venda = df_orc[(df_orc['DATA'] == data_o) & (df_orc['CLIENTE'] == cli_o)]
            
            st.info(f"✅ Orçamento de **{cli_o}** carregado com sucesso!")

            # 2. EXIBIÇÃO DOS ITENS QUE SERÃO VENDIDOS
            st.write("### Itens da Venda")
            total_venda = 0
            for i, row in itens_venda.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.write(f"**{row['PRODUTO']}**")
                    c1.caption(f"Detalhes: {row['DETALHES']}")
                    c2.write(f"Qtd: {row['QT']}")
                    c3.write(f"Unit: R$ {row['VALOR UNITARIO']:,.2f}")
                    c4.write(f"Total: R$ {row['VALOR TOTAL']:,.2f}")
                    total_venda += row['VALOR TOTAL']
            
            st.subheader(f"💰 Total da Venda: R$ {total_venda:,.2f}")
            
            # 3. DADOS COMPLEMENTARES DA VENDA
            col_v1, col_v2 = st.columns(2)
            forma_pgto = col_v1.selectbox("Forma de Pagamento", ["BOLETO", "PIX", "CARTÃO", "TRANSFERÊNCIA"])
            nf_numero = col_v2.text_input("Número da Nota Fiscal (opcional)")

            # 4. BOTÃO DE EFETIVAR
            if st.button("🚀 CONFIRMAR VENDA E BAIXAR ESTOQUE", use_container_width=True, type="primary"):
                try:
                    # Preparamos os dados para a planilha de Vendas
                    novas_vendas = []
                    for _, it in itens_venda.iterrows():
                        novas_vendas.append({
                            "DATA_VENDA": datetime.now().strftime("%d/%m/%Y"),
                            "CLIENTE": cli_o,
                            "PRODUTO": it["PRODUTO"],
                            "QT": it["QT"],
                            "VALOR_TOTAL": it["VALOR TOTAL"],
                            "FORMA_PGTO": forma_pgto,
                            "NF": nf_numero,
                            "VENDEDOR": st.session_state.get('usuario', 'SISTEMA'),
                            "REF_ORCAMENTO": data_o # Mantém o vínculo com o orçamento original
                        })
                    
                    # Salva na aba Vendas
                    df_vendas_atual = conn.read(worksheet="Vendas", ttl=0).dropna(how='all')
                    df_vendas_final = pd.concat([df_vendas_atual, pd.DataFrame(novas_vendas)], ignore_index=True)
                    conn.update(worksheet="Vendas", data=df_vendas_final)
                    
                    st.success(f"🎉 Venda de {cli_o} registrada com sucesso!")
                    st.balloons()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao registrar venda: {e}")
    else:
        st.warning("Nenhum orçamento encontrado no sistema.")