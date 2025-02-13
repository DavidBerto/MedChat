from openai import OpenAI
import streamlit as st
import numpy as np
import openai
from PIL import Image, ImageDraw
import os

load_dotenv()

api_key = os.environ.get("OPENAI_API_KEY")
st.title("Clínica Especializada em Traumatologia")

#configuração de foto

client = OpenAI(api_key=api_key)

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o-mini"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
                "role": "assistant",
                "content": """Olá! Sou a secretária virtual do consultório. Como posso te ajudar?
                """
                
            }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("""Como posso ajudar?"""):
    #st.chat_message("user", avatar=imageAI)
    with st.chat_message("user"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        #st.chat_message("user").write(msg_user)
        st.markdown(prompt)

    with st.chat_message("ai"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {
                    "role": "system",
                    "content": """seu nome é Paula e Você é uma secretária virtual de consultório médico chamado "Clínica Especializada em Traumatologia".
                    paciente vao entrar com contato para sanar dúvidas relacionadas as traumatologia e reumatologia, fazer agendamentos de consultas.
                    seu trabalho é sanar dúvidas comuns dos pacientes, fazer agendamento de consultas
                     
                    caso haja algum assunto relacionalo com reumatologia ou traumatologia, indique a falar com um dos médicos do seu consultorio
                    caso haja pedido de agendamento, Extraia as informações de agendamento da mensagem do usuário no formato JSON:
                    {
                        "acao": "agendar" ou "consultar",
                        "medico": "nome do médico" (se mencionado),
                        "data": "YYYY-MM-DD" (se mencionada),
                        "hora": "HH:MM" (se mencionada),
                        "paciente": "nome do paciente" (se mencionado)
                    }
                    Se a mensagem não contiver informações de agendamento, responda normalmente.
                    
                    é extremamente importante que fornece apenas respostas concisas com informaç~eos relevantes e seja empatica com o paciente.
                    
                    responda apenas em portugues brasileiro. é extritametne proibido responder em outra lingua que nao seja portugues."""
                },
                {"role": "system", "content": prompt}
#                for m in st.session_state.messages
            ],
            stream=True, temperature=0.7
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "ai", "content": response})
