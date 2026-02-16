import streamlit as st
import requests
import json



st.set_page_config(page_title="Postgres AI Chat", page_icon="🤖", layout="wide")

st.header("New User Creation")
name = st.text_input("User Name")

db_user = st.text_input("db user")
db_pass = st.text_input("db pass")
db_host = st.text_input("db host")
db_port = st.text_input("db port")
db_name = st.text_input("db name")

if st.button("Create New User"):
    db_credentials = {'db_user':db_user, 'db_pass':db_pass, 'db_host':db_host, 'db_port':db_port, 'db_name':db_name}
    payload = {"name":name, 'db_credentials':db_credentials}
    api_url = "http://127.0.0.1:8000/newuser"
    response = requests.post(api_url, data=json.dumps(payload))
    pass

st.title("🤖 Grafana AI Assistant")
st.markdown("Chat interactivo con visualización de Tools y Metadatos.")

def test_chat_grafana_api(
    human_message: str,
    user_id: int,
    chat_id: int,
    api_url: str,
):
    """
    Envía el mensaje a la API y maneja errores.
    """


    # api_url = f"http://127.0.0.1:8000/runchat"
    payload = {"human_message": human_message, "user_id":user_id, "chat_id":chat_id}

    try:
        response = requests.post(api_url, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = f"Error de conexión: {str(e)}"
        if hasattr(e, "response") and e.response is not None:
            error_msg += f"\nDetalle: {e.response.text}"
        return {"error": error_msg}


# ==========================================
# 3. Componentes de UI Personalizados
# ==========================================

def render_tool_call(tool_calls):
    """Renderiza visualmente la llamada a una herramienta."""
    for tool in tool_calls:
        with st.container():
            st.markdown(f"#### 🛠️ AI Solicitando Tool: `{tool.get('name', 'Unknown')}`")
            with st.expander("Ver argumentos de la tool", expanded=False):
                st.json(tool.get("args", {}))

def render_tool_output(content, tool_name):
    """Renderiza la respuesta de la herramienta."""
    st.info(f"**⚙️ Output de Tool ({tool_name}):**\n\n{content}", icon="⚙️")

def render_metadata(usage_metadata):
    """Muestra los tokens usados en un formato pequeño."""
    if usage_metadata:
        input_tokens = usage_metadata.get('input_tokens', 0)
        output_tokens = usage_metadata.get('output_tokens', 0)
        total_tokens = usage_metadata.get('total_tokens', 0)
        
        st.caption(
            f"📊 **Metadatos:** Input: `{input_tokens}` | Output: `{output_tokens}` | Total: `{total_tokens}`"
        )


def process_api_response(response_list):
    """
    Itera sobre la lista 'chat_response' y renderiza cada elemento
    según el nuevo formato de la API:
      - type: "Ai"
      - type: "Tool"
    """

    for item in response_list:
        item_type = item.get("type")
        content = item.get("content", "")
        tool_calls = item.get("tool_calls", [])
        usage_metadata = item.get("usage_metadata", {})

        # ==========================================
        # 🧠 Caso 1: Mensaje de la IA
        # ==========================================
        if item_type == "Ai":

            # Si la IA está llamando tools
            if tool_calls:
                st.warning("🔄 La IA está ejecutando acciones...")
                render_tool_call(tool_calls)

            # Si hay contenido textual
            if content:
                st.markdown(content)

            # Mostrar metadata si existe
            if usage_metadata:
                render_metadata(usage_metadata)

            st.divider()

        # ==========================================
        # ⚙️ Caso 2: Respuesta de Tool
        # ==========================================
        elif item_type == "Tool":
            tool_name = item.get("name", "Unknown Tool")

            # Intentar parsear JSON si es string JSON
            try:
                parsed_content = json.loads(content)
                render_tool_output(parsed_content, tool_name)
            except (json.JSONDecodeError, TypeError):
                render_tool_output(content, tool_name)

            st.divider()

        # ==========================================
        # 🛑 Caso desconocido
        # ==========================================
        else:
            st.error(f"Tipo de mensaje desconocido: {item_type}")
            st.json(item)
            st.divider()


# ==========================================
# 4. Sidebar: Configuración
# ==========================================
with st.sidebar:
    st.header("Configuración")
    user_id = st.number_input("user_id", min_value=1, value=1, step=1)
    chat_id = st.number_input("chat_id", min_value=1, value=1, step=1)
    api_url = st.text_input(
        "API URL", 
        value="http://127.0.0.1:8000/runchat"
    )
    
    if st.button("Limpiar Historial"):
        st.session_state.messages = []
        st.rerun()


# ==========================================
# 5. Gestión del Estado (Chat History)
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []


# ==========================================
# 6. Renderizar Historial de Chat
# ==========================================
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    else:
        # El mensaje del asistente contiene la estructura compleja JSON
        with st.chat_message("assistant"):
            if "error" in message:
                st.error(message["error"])
            else:
                process_api_response(message["content"])

# ==========================================
# 7. Input del Usuario y Lógica Principal
# ==========================================
if prompt := st.chat_input("Escribe tu mensaje para Grafana..."):
    # 1. Mostrar mensaje del usuario
    st.chat_message("user").markdown(prompt)
    # 2. Guardar en historial
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 3. Llamar a la API
    with st.chat_message("assistant"):
        with st.spinner("Consultando a Grafana AI..."):
            response_data = test_chat_grafana_api(human_message=prompt, user_id=user_id, chat_id=chat_id, api_url=api_url)
        
        # 4. Procesar y Mostrar Respuesta
        if "error" in response_data:
            st.error(response_data["error"])
            st.session_state.messages.append({"role": "assistant", "error": response_data["error"]})
        else:
            chat_response_list = response_data.get("chat_response", [])
            process_api_response(chat_response_list)
            
            # 5. Guardar la respuesta compleja en el historial
            st.session_state.messages.append({"role": "assistant", "content": chat_response_list})