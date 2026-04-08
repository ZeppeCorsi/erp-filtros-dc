def aba_gastos_cartao():
    st.subheader("💳 Registro de Gastos no Cartão")
    
    with st.form("form_cartao", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            data_compra = st.date_input("Data da Compra", value=date.today())
            descricao = st.text_input("Descrição do Gasto")
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
            
        with col2:
            st.info("Configuração da Fatura")
            # Data em que o dinheiro efetivamente sai do seu Fluxo de Caixa
            data_pagamento_fatura = st.date_input("Data de Vencimento da Fatura")
            
        btn_salvar = st.form_submit_button("Registrar Gasto")

    if btn_salvar:
        if descricao and valor > 0:
            try:
                # 1. Gravar na aba 'Gastos Cartao' (Histórico de compras)
                dados_cartao = pd.DataFrame([{
                    "DATA": data_compra.strftime("%d/%m/%Y"),
                    "DESCRICAO": descricao,
                    "VALOR": valor,
                    "PAGAMENTO_FATURA": data_pagamento_fatura.strftime("%d/%m/%Y")
                }])
                
                conn.create(worksheet="Gastos Cartao", data=dados_cartao)

                # 2. Gravar no 'Fluxo de Caixa' como PENDENTE (Saída futura)
                dados_fluxo = pd.DataFrame([{
                    "DATA": data_pagamento_fatura.strftime("%d/%m/%Y"),
                    "TIPO": "SAIDA",
                    "DESCRICAO": f"CARTÃO: {descricao}",
                    "VALOR": valor,
                    "PARCELA": "1/1",
                    "STATUS": "PENDENTE",
                    "CLIENTE": "FILTROS DC",
                    "NF": "FATURA"
                }])
                
                conn.create(worksheet="Fluxo de Caixa", data=dados_fluxo)
                
                st.success(f"Gasto registrado! Lançamento de R$ {valor:.2f} enviado ao Fluxo para o dia {data_pagamento_fatura.strftime('%d/%m/%Y')}.")
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
        else:
            st.warning("Preencha a descrição e o valor corretamente.")

# Para exibir, chame a função:
# aba_gastos_cartao()