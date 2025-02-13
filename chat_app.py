import streamlit as st
import openai
from datetime import datetime, timedelta
import json

# Configuração da página
st.set_page_config(page_title="Consultório Médico - Agendamento", layout="wide")

# Inicialização das variáveis de estado
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Simulação de banco de dados de médicos e horários
DOCTORS_DB = {
    "Dra. Maria Silva": {
        "especialidade": "Clínica Geral",
        "horarios_disponiveis": [
            "09:00", "10:00", "11:00", "14:00", "15:00", "16:00"
        ]
    },
    "Dr. João Santos": {
        "especialidade": "Cardiologia",
        "horarios_disponiveis": [
            "08:00", "09:00", "10:00", "14:00", "15:00"
        ]
    }
}

# Prompt da persona secretária
SECRETARY_PROMPT = """Você é a Ana, uma secretária virtual profissional e atenciosa de um consultório médico.
Suas responsabilidades incluem:
1. Dar boas-vindas aos pacientes
2. Auxiliar no agendamento e remarcação de consultas
3. Informar sobre os médicos disponíveis e suas especialidades
4. Verificar horários disponíveis
5. Confirmar agendamentos

Diretrizes de comportamento:
- Seja sempre cordial e profissional
- Use linguagem clara e acessível
- Peça informações necessárias como nome do paciente e preferência de horário
- Confirme todos os dados antes de finalizar agendamentos
- Em caso de dúvidas, peça esclarecimentos

Médicos e horários disponíveis:
{doctors_db}

Por favor, interaja com o paciente seguindo essas diretrizes."""

def get_openai_response(messages):
    """Função para obter resposta do ChatGPT"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SECRETARY_PROMPT.format(doctors_db=json.dumps(DOCTORS_DB, indent=2))},
                *messages
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Desculpe, ocorreu um erro na comunicação. Por favor, tente novamente. Erro: {str(e)}"

# Interface principal
st.title("🏥 Consultório Médico - Agendamento Online")
st.markdown("---")

# Sidebar com informações dos médicos
with st.sidebar:
    st.header("📋 Médicos Disponíveis")
    for medico, info in DOCTORS_DB.items():
        st.subheader(medico)
        st.write(f"Especialidade: {info['especialidade']}")
        st.write("Horários disponíveis:")
        for horario in info['horarios_disponiveis']:
            st.write(f"- {horario}")
        st.markdown("---")

# Área principal do chat
st.header("💬 Chat com a Secretária Virtual")

# Exibir mensagens anteriores
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input do usuário
if prompt := st.chat_input("Digite sua mensagem..."):
    # Adicionar mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Obter e exibir resposta da secretária virtual
    with st.chat_message("assistant"):
        response = get_openai_response(st.session_state.messages)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# Informações adicionais
with st.expander("ℹ️ Informações Importantes"):
    st.write("""
    - Para agendar uma consulta, informe sua preferência de médico e horário
    - Em caso de remarcação, informe o horário atual e o desejado
    - Mantenha seu cadastro atualizado
    - Em caso de emergência, procure atendimento imediato
    """)