import streamlit as st
import openai
from datetime import datetime, timedelta
import pytz
import json

# Configuração da API do OpenAI
openai.api_key = st.secrets["OPENAI_API_KEY"]

class AgendamentoManager:
    def __init__(self):
        if 'consultas' not in st.session_state:
            st.session_state.consultas = []
        if 'horarios_disponiveis' not in st.session_state:
            # Horários de 8h às 18h, a cada 30 minutos
            st.session_state.horarios_disponiveis = [
                f"{h:02d}:{m:02d}" 
                for h in range(8, 18) 
                for m in [0, 30]
            ]
    
    def verificar_disponibilidade(self, data, hora):
        """Verifica se o horário está disponível na data especificada"""
        for consulta in st.session_state.consultas:
            if consulta['data'] == data and consulta['hora'] == hora:
                return False
        return True
    
    def agendar_consulta(self, medico, data, hora, paciente):
        """Agenda uma nova consulta"""
        if not self.verificar_disponibilidade(data, hora):
            return False, "Horário já ocupado"
        
        consulta = {
            'id': len(st.session_state.consultas) + 1,
            'medico': medico,
            'paciente': paciente,
            'data': data,
            'hora': hora,
            'status': 'confirmado'
        }
        
        st.session_state.consultas.append(consulta)
        return True, f"Consulta agendada com sucesso! ID: {consulta['id']}"
    
    def obter_horarios_disponiveis(self, data):
        """Retorna horários disponíveis para a data"""
        horarios = st.session_state.horarios_disponiveis.copy()
        
        # Remove horários já agendados
        for consulta in st.session_state.consultas:
            if consulta['data'] == data and consulta['hora'] in horarios:
                horarios.remove(consulta['hora'])
        
        return horarios
    
    def processar_comando_chat(self, mensagem):
        """Processa comandos de agendamento via chat"""
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Você é uma secretária virtual de consultório médico.
                        seu trabalho é sanar dúvidas comuns dos pacientes e fazer agendamento de consultas 
                        Extraia as informações de agendamento da mensagem do usuário no formato JSON:
                        {
                            "acao": "agendar" ou "consultar",
                            "medico": "nome do médico" (se mencionado),
                            "data": "YYYY-MM-DD" (se mencionada),
                            "hora": "HH:MM" (se mencionada),
                            "paciente": "nome do paciente" (se mencionado)
                        }
                        Se a mensagem não contiver informações de agendamento, responda normalmente."""
                    },
                    {"role": "user", "content": mensagem}
                ],
                temperature=0.7
            )
            
            resposta = response.choices[0].message.content.strip()
            
            # Tenta extrair JSON da resposta
            try:
                inicio_json = resposta.find('{')
                fim_json = resposta.rfind('}') + 1
                if inicio_json >= 0 and fim_json > 0:
                    json_str = resposta[inicio_json:fim_json]
                    dados = json.loads(json_str)
                    
                    if dados.get('acao') == 'agendar':
                        if all(k in dados for k in ['medico', 'data', 'hora', 'paciente']):
                            sucesso, msg = self.agendar_consulta(
                                dados['medico'],
                                dados['data'],
                                dados['hora'],
                                dados['paciente']
                            )
                            return f"{resposta}\n\n{'✅' if sucesso else '❌'} {msg}"
                    
                    elif dados.get('acao') == 'consultar':
                        if dados.get('data'):
                            horarios = self.obter_horarios_disponiveis(dados['data'])
                            return f"Horários disponíveis para {dados['data']}:\n" + \
                                   "\n".join(horarios)
                
                return resposta
            
            except json.JSONDecodeError:
                return resposta
            
        except Exception as e:
            return f"Desculpe, ocorreu um erro: {str(e)}"

def main():
    st.title("📅 Consultas Médicas de Traumatologia")
    
    # Inicializar o gerenciador de agendamentos
    agendamento = AgendamentoManager()
    
    # Área de chat
    st.subheader("💬 Chat com a Secretária Virtual")
    
    # Inicializar histórico de chat
    if 'mensagens' not in st.session_state:
        st.session_state.mensagens = [
            {
                "role": "assistant",
                "content": """Olá! Sou a secretária virtual do consultório. 
                Posso ajudar você a:
                
                - Sanara Dúvidas
                - Agendar uma consulta
                - Verificar horários disponíveis
                """
            }
        ]
    
    # Mostrar histórico
    for msg in st.session_state.mensagens:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Input do usuário
    user_input = st.chat_input("Digite sua mensagem:")
    
    if user_input:
        # Adicionar mensagem do usuário ao histórico
        st.session_state.mensagens.append({"role": "user", "content": user_input})
        
        # Processar mensagem
        resposta = agendamento.processar_comando_chat(user_input)
        
        # Adicionar resposta ao histórico
        st.session_state.mensagens.append({"role": "assistant", "content": resposta})
        
        # Atualizar chat
        st.rerun()
    
    # Visualização das consultas agendadas
    if st.session_state.consultas:
        with st.expander("📋 Consultas Agendadas"):
            for consulta in st.session_state.consultas:
                st.write(f"""
                🏥 Consulta #{consulta['id']}
                👨‍⚕️ Médico: {consulta['medico']}
                👤 Paciente: {consulta['paciente']}
                📅 Data: {consulta['data']}
                🕒 Hora: {consulta['hora']}
                ✅ Status: {consulta['status']}
                """)

if __name__ == "__main__":
    main()