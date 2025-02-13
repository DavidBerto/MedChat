import streamlit as st
import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import json
import os

# Configurações das APIs
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Escopo do Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """
    Configura e retorna o serviço do Google Calendar usando credenciais do Streamlit secrets.
    """
    try:
        # Obter credenciais do Google das secrets do Streamlit
        creds_info = {
            "token": st.secrets["GOOGLE_TOKEN"],
            "refresh_token": st.secrets["GOOGLE_REFRESH_TOKEN"],
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": st.secrets["GOOGLE_CLIENT_ID"],
            "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
            "scopes": SCOPES
        }
        
        creds = Credentials.from_authorized_user_info(info=creds_info, scopes=SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise Exception("Credenciais inválidas")
        
        service = build('calendar', 'v3', credentials=creds)
        return service
    
    except Exception as e:
        st.error(f"Erro na autenticação: {str(e)}")
        return None

def chat_with_gpt(prompt):
    """
    Interage com o GPT-3.5 usando a API mais recente.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é uma secretária virtual de consultório médico, profissional e prestativa."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Erro na comunicação com OpenAI: {str(e)}")
        return "Desculpe, estou com problemas técnicos no momento."

def verificar_conflitos(service, start_time, end_time, calendar_id='primary'):
    """
    Verifica se há conflitos de horário no período especificado.
    """
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return len(events_result.get('items', [])) > 0
    except Exception as e:
        st.error(f"Erro ao verificar conflitos: {str(e)}")
        return True

def marcar_consulta(service, medico, data, hora, paciente):
    """
    Marca uma consulta no Google Calendar.
    """
    try:
        # Converter string de data e hora para datetime
        data_hora = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M")
        fuso_horario = pytz.timezone('America/Sao_Paulo')
        data_hora = fuso_horario.localize(data_hora)
        
        fim_consulta = data_hora + timedelta(minutes=30)
        
        # Verificar conflitos
        if verificar_conflitos(service, data_hora, fim_consulta):
            return False, "Horário já ocupado"
        
        evento = {
            'summary': f'Consulta - Dr(a). {medico}',
            'description': f'Paciente: {paciente}',
            'start': {
                'dateTime': data_hora.isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': fim_consulta.isoformat(),
                'timeZone': 'America/Sao_Paulo',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        service.events().insert(calendarId='primary', body=evento).execute()
        return True, "Consulta marcada com sucesso!"
        
    except Exception as e:
        return False, f"Erro ao marcar consulta: {str(e)}"

def remarcar_consulta(service, event_id, nova_data, nova_hora):
    """
    Remarca uma consulta existente para novo horário.
    """
    try:
        # Converter nova data e hora
        nova_data_hora = datetime.strptime(f"{nova_data} {nova_hora}", "%Y-%m-%d %H:%M")
        fuso_horario = pytz.timezone('America/Sao_Paulo')
        nova_data_hora = fuso_horario.localize(nova_data_hora)
        fim_consulta = nova_data_hora + timedelta(minutes=30)
        
        # Verificar conflitos no novo horário
        if verificar_conflitos(service, nova_data_hora, fim_consulta):
            return False, "Novo horário já está ocupado"
        
        # Buscar evento existente
        evento = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Atualizar horários
        evento['start']['dateTime'] = nova_data_hora.isoformat()
        evento['end']['dateTime'] = fim_consulta.isoformat()
        
        service.events().update(calendarId='primary', eventId=event_id, body=evento).execute()
        return True, "Consulta remarcada com sucesso!"
        
    except Exception as e:
        return False, f"Erro ao remarcar consulta: {str(e)}"

def obter_horarios_disponiveis(service, medico, data):
    """
    Retorna lista de horários disponíveis para uma data específica.
    """
    try:
        data_inicio = datetime.strptime(data, "%Y-%m-%d").replace(hour=8, minute=0)  # Início às 8h
        data_fim = data_inicio.replace(hour=18, minute=0)  # Fim às 18h
        fuso_horario = pytz.timezone('America/Sao_Paulo')
        data_inicio = fuso_horario.localize(data_inicio)
        data_fim = fuso_horario.localize(data_fim)
        
        # Buscar eventos do dia
        events_result = service.events().list(
            calendarId='primary',
            timeMin=data_inicio.isoformat(),
            timeMax=data_fim.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        eventos = events_result.get('items', [])
        horarios_ocupados = set()
        
        # Marcar horários ocupados
        for evento in eventos:
            inicio = datetime.fromisoformat(evento['start']['dateTime'].replace('Z', '+00:00'))
            fim = datetime.fromisoformat(evento['end']['dateTime'].replace('Z', '+00:00'))
            
            while inicio < fim:
                horarios_ocupados.add(inicio.strftime("%H:%M"))
                inicio += timedelta(minutes=30)
        
        # Gerar todos os horários possíveis
        horarios_disponiveis = []
        hora_atual = data_inicio
        
        while hora_atual < data_fim:
            horario = hora_atual.strftime("%H:%M")
            if horario not in horarios_ocupados:
                horarios_disponiveis.append(horario)
            hora_atual += timedelta(minutes=30)
        
        return horarios_disponiveis
        
    except Exception as e:
        st.error(f"Erro ao buscar horários disponíveis: {str(e)}")
        return []

def main():
    st.title("📅 Agendamento de Consultas Médicas")
    
    # Verificar se todas as secrets necessárias estão configuradas
    required_secrets = [
        "OPENAI_API_KEY",
        "GOOGLE_TOKEN",
        "GOOGLE_REFRESH_TOKEN",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET"
    ]
    
    missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]
    if missing_secrets:
        st.error(f"Faltam as seguintes configurações: {', '.join(missing_secrets)}")
        st.info("Configure estas variáveis no arquivo .streamlit/secrets.toml")
        return
    
    # Inicializar o serviço do Calendar
    service = get_calendar_service()
    if not service:
        st.error("Não foi possível conectar ao Google Calendar")
        return
    
    # Área de chat
    st.subheader("💬 Chat com a Secretária Virtual")
    
    # Inicializar histórico de chat na sessão
    if 'mensagens' not in st.session_state:
        st.session_state.mensagens = []
    
    # Mostrar histórico
    for msg in st.session_state.mensagens:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Input do usuário
    user_input = st.chat_input("Digite sua mensagem:")
    
    if user_input:
        # Adicionar mensagem do usuário ao histórico
        st.session_state.mensagens.append({"role": "user", "content": user_input})
        
        # Processar input
        prompt = f"Usuário: {user_input}\nPor favor, responda de forma profissional e clara."
        response = chat_with_gpt(prompt)
        
        # Adicionar resposta ao histórico
        st.session_state.mensagens.append({"role": "assistant", "content": response})
        
        # Atualizar chat
        st.experimental_rerun()
        
        # Processar ações baseadas no input
        input_lower = user_input.lower()
        if "agendar" in input_lower or "marcar" in input_lower:
            with st.expander("🗓️ Agendar Nova Consulta"):
                medicos = ["Dr. Silva", "Dra. Santos", "Dr. Oliveira"]
                medico = st.selectbox("Selecione o médico:", medicos)
                data = st.date_input("Selecione a data:")
                
                if data:
                    horarios = obter_horarios_disponiveis(service, medico, data.strftime("%Y-%m-%d"))
                    if horarios:
                        hora = st.selectbox("Horários disponíveis:", horarios)
                        paciente = st.text_input("Nome do paciente:")
                        
                        if st.button("Confirmar Agendamento"):
                            sucesso, mensagem = marcar_consulta(
                                service, medico, data.strftime("%Y-%m-%d"), 
                                hora, paciente
                            )
                            if sucesso:
                                st.success(mensagem)
                            else:
                                st.error(mensagem)
                    else:
                        st.warning("Não há horários disponíveis nesta data.")
        
        elif "remarcar" in input_lower:
            with st.expander("🔄 Remarcar Consulta"):
                event_id = st.text_input("ID da consulta:")
                nova_data = st.date_input("Nova data:")
                
                if nova_data:
                    horarios = obter_horarios_disponiveis(service, "", nova_data.strftime("%Y-%m-%d"))
                    if horarios:
                        nova_hora = st.selectbox("Novo horário:", horarios)
                        
                        if st.button("Confirmar Remarcação"):
                            sucesso, mensagem = remarcar_consulta(
                                service, event_id, nova_data.strftime("%Y-%m-%d"), 
                                nova_hora
                            )
                            if sucesso:
                                st.success(mensagem)
                            else:
                                st.error(mensagem)
                    else:
                        st.warning("Não há horários disponíveis nesta data.")

if __name__ == "__main__":
    main()