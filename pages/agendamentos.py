import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date, timedelta
import calendar
import urllib.parse  # Essencial para criar o link do Outlook

# 1. CONFIGURAÇÃO E SEGURANÇA
if 'logado' not in st.session_state or not st.session_state.logado:
    st.error("🚫 Acesso negado! Faça login na Home.")
    st.stop()

st.set_page_config(page_title="Agenda | Filtros DC", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# IDs e URLs
ID_P = "1e4OxEVcNSdvi0NehhTgt0zvWK9ncAgGQa1E6WAEgFE8"
URL_C = f"https://docs.google.com/spreadsheets/d/{ID_P}/gviz/tq?tqx=out:csv&sheet=Clientes"

# --- FUNÇÃO AUXILIAR: LINK DO OUTLOOK ---
def gerar_link_outlook(cliente, data_str, hora_str, servico, contato, obs):
    try:
        # Converte a data e hora para objeto datetime
        data_dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")
        fim_dt = data_dt + timedelta(hours=1) # Duração padrão de 1h
        
        assunto = f"{servico}: {cliente}"
        corpo = f"CONTATO: {contato}\nSERVIÇO: {servico}\nOBSERVAÇÕES: {obs}"
        
        # Parâmetros para o Deep Link do Outlook Web
        params = {
            "path": "/calendar/action/compose",
            "rru": "addevent",
            "subject": assunto,
            "startdt": data_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "enddt": fim_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "body": corpo
        }
        return "https://outlook.office.com/calendar/0/deeplink/compose?" + urllib.parse.urlencode(params)
    except:
        return "#"
    
    
@st.cache_data(ttl=2)
def carregar_clientes():
    try:
        df = pd.read_csv(URL_C)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except: return pd.DataFrame()

df_clientes = carregar_clientes()

@st.dialog("🔄 Reagendar Visita")
def reagendar_dialog(indice, dados):
    st.markdown(f"### Reagendamento: {dados['CLIENTE']}")
    st.info(f"Horário atual: {dados['DATA_SERVICO']} às {dados['HORA']}")
    
    c1, c2 = st.columns(2)
    nova_data = c1.date_input("Nova Data", value=datetime.now(), format="DD/MM/YYYY")
    nova_hora = c2.time_input("Novo Horário", value=datetime.strptime("09:00", "%H:%M").time())
    
    motivo = st.text_area("Motivo do Reagendamento (será salvo nas observações)").upper()
    
    if st.button("💾 CONFIRMAR REAGENDAMENTO", use_container_width=True):
        try:
            # Lendo a base completa para atualizar a linha correta
            df_full = conn.read(worksheet="Agendamentos", ttl=0)
            
            # Atualizando os campos
            df_full.at[indice, 'DATA_SERVICO'] = nova_data.strftime("%d/%m/%Y")
            df_full.at[indice, 'HORA'] = nova_hora.strftime("%H:%M")
            
            # Mantém a observação antiga e adiciona o motivo do reagendamento
            obs_antiga = str(dados.get('OBS', '')) if str(dados.get('OBS', '')) != 'nan' else ""
            df_full.at[indice, 'OBS'] = f"{obs_antiga} | REAGENDADO: {motivo}".strip(" | ")
            
            conn.update(worksheet="Agendamentos", data=df_full)
            st.success("Calendário atualizado com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

st.title("📅 Agenda de Serviços Filtros DC")

# --- NAVEGAÇÃO DO MÊS ---
if 'mes_ref' not in st.session_state:
    st.session_state.mes_ref = datetime.now().date().replace(day=1)

c_nav1, c_nav2, c_nav3 = st.columns([1, 2, 1])
if c_nav1.button("⬅️ Mês Anterior"):
    st.session_state.mes_ref = (st.session_state.mes_ref - timedelta(days=1)).replace(day=1)
    st.rerun()

meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
c_nav2.markdown(f"<h2 style='text-align: center;'>{meses_pt[st.session_state.mes_ref.month - 1]} {st.session_state.mes_ref.year}</h2>", unsafe_allow_html=True)

if c_nav3.button("Próximo Mês ➡️"):
    st.session_state.mes_ref = (st.session_state.mes_ref + timedelta(days=32)).replace(day=1)
    st.rerun()

# --- FORMULÁRIO DE ENTRADA ---
with st.expander("➕ Lançar Novo Agendamento", expanded=False):
    with st.form("form_novo_servico"):
        f1, f2, f3 = st.columns([2, 1, 1])
        cliente_sel = f1.selectbox("Cliente", options=sorted(df_clientes['NOME REDUZIDO'].tolist()) if not df_clientes.empty else ["-"])
        data_sel = f2.date_input("Data do Serviço", value=datetime.now(), format="DD/MM/YYYY")
        hora_sel = f3.time_input("Horário", value=datetime.strptime("09:00", "%H:%M").time())
        
        f4, f5 = st.columns(2)
        tipo_sel = f4.selectbox("Tipo de Serviço", ["INSTALAÇÃO", "TROCA DE REFIL", "MANUTENÇÃO", "VISITA TÉCNICA"])
        contato_sel = f5.text_input("Telefone de Contato")
        
        obs_sel = st.text_area("Observações Técnicas").upper()
        
        if st.form_submit_button("✅ CONFIRMAR AGENDAMENTO"):
            try:
                df_atual = conn.read(worksheet="Agendamentos", ttl=0)
                nova_linha = pd.DataFrame([{
                    "DATA_SERVICO": data_sel.strftime("%d/%m/%Y"),
                    "HORA": hora_sel.strftime("%H:%M"),
                    "CLIENTE": cliente_sel,
                    "SERVICO": tipo_sel,
                    "CONTATO": contato_sel,
                    "STATUS": "AGENDADO",
                    "OBS": obs_sel
                }])
                conn.update(worksheet="Agendamentos", data=pd.concat([df_atual, nova_linha], ignore_index=True))
                st.success(f"Agendado com sucesso para {data_sel.strftime('%d/%m/%Y')}!")
                st.rerun()
            except: st.error("Erro ao salvar. Verifique se a aba 'Agendamentos' existe.")

# --- CALENDÁRIO VISUAL ---
st.divider()
try:
    df_ag = conn.read(worksheet="Agendamentos", ttl=0)
    df_ag.columns = [str(c).strip().upper() for c in df_ag.columns]

    # Cabeçalho dos dias
    dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    cols_h = st.columns(7)
    for i, d in enumerate(dias_semana):
        cols_h[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#555;'>{d}</div>", unsafe_allow_html=True)

    # Matriz do calendário
    cal_matriz = calendar.monthcalendar(st.session_state.mes_ref.year, st.session_state.mes_ref.month)

    for semana in cal_matriz:
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            if dia != 0:
                with cols[i]:
                    data_loop = date(st.session_state.mes_ref.year, st.session_state.mes_ref.month, dia)
                    data_loop_str = data_loop.strftime("%d/%m/%Y")
                    
                    cor_dia = "#FF4B4B" if data_loop == date.today() else "#31333F"
                    st.markdown(f"<p style='margin-bottom:5px; color:{cor_dia}; font-weight:bold;'>{dia}</p>", unsafe_allow_html=True)
                    
                    # Filtra serviços do dia
                    servs_dia = df_ag[df_ag['DATA_SERVICO'] == data_loop_str]
                    
                    for _, s in servs_dia.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{s['HORA']}**")
                            st.markdown(f"<p style='font-size:12px; margin:0;'>👤 {s['CLIENTE']}</p>", unsafe_allow_html=True)
                            if str(s.get('CONTATO','')) != 'nan':
                                st.markdown(f"<p style='font-size:11px; color:#0078D4; margin:0;'>📞 {s['CONTATO']}</p>", unsafe_allow_html=True)
                            st.caption(f"🛠️ {s['SERVICO']}")
                            
                            # BOTÃO OUTLOOK
                            url_out = gerar_link_outlook(
                                s['CLIENTE'], s['DATA_SERVICO'], s['HORA'], 
                                s['SERVICO'], s.get('CONTATO',''), s.get('OBS','')
                            )
                            st.link_button("📅 Outlook", url_out, use_container_width=True)

                            # BOTÃO OUTLOOK
                            url_out = gerar_link_outlook(
                                s['CLIENTE'], s['DATA_SERVICO'], s['HORA'], 
                                s['SERVICO'], s.get('CONTATO',''), s.get('OBS','')
                            )
                            st.link_button("📅 Outlook", url_out, use_container_width=True)

                            # --- INCLUA ESTE BLOCO ABAIXO ---
                            if st.button("🔄 Reagendar", key=f"reag_{_}", use_container_width=True):
                                reagendar_dialog(_, s) 
                            # -------------------------------

                            # OBSERVAÇÕES
                            if str(s.get('OBS','')) != 'nan' and s.get('OBS'):
                                with st.expander("🔎 Obs"):
                                    st.write(s['OBS'])
            else:
                cols[i].write("")
except Exception as e:
    st.info("Aguardando lançamentos na aba 'Agendamentos'...")

st.sidebar.image("LOGO Horizontal.jpg", use_container_width=True)