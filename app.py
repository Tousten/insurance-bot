# Car Insurance Lead Bot - Complete Working Version
from flask import Flask, render_template_string, request, jsonify
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '@Toustten')

conversations = {}

def send_telegram_photo(photo_data, caption, filename):
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {'photo': (filename, photo_data, 'image/jpeg')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        return response.status_code == 200
    except:
        return False

def send_telegram_document(doc_data, caption, filename):
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        files = {'document': (filename, doc_data, 'application/pdf')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        return response.status_code == 200
    except:
        return False

def send_contact_info_to_telegram(session_id):
    """Send contact info to Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        return
    
    conv = conversations.get(session_id, {})
    contact = conv.get('contact_info', {})
    
    if not contact.get('name'):
        return
    
    text = f"""📋 INFORMACOES DO CLIENTE

Nome: {contact.get('name', 'Nao informado')}
Cidade: {contact.get('city', 'Nao informado')}
Sessao: {session_id[:15]}..."""
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seguro Auto</title>
    <style>
        body { font-family: sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; margin: 0; }
        .chat-container { width: 100%; max-width: 420px; height: 85vh; background: white; border-radius: 24px; box-shadow: 0 25px 80px rgba(0,0,0,0.4); display: flex; flex-direction: column; overflow: hidden; }
        .chat-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; text-align: center; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 20px; }
        .message { max-width: 85%; padding: 14px 18px; border-radius: 20px; margin-bottom: 10px; font-size: 0.95rem; }
        .message.bot { background: #f0f2f5; color: #1a1a1a; margin-right: auto; }
        .message.user { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; margin-left: auto; }
        .chat-input { padding: 18px; border-top: 1px solid #e8e8e8; display: flex; gap: 12px; background: #fafafa; }
        .chat-input input[type="text"] { flex: 1; padding: 14px 20px; border: 2px solid #e0e0e0; border-radius: 28px; font-size: 0.95rem; }
        .chat-input button { width: 50px; height: 50px; border: none; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-size: 1.2rem; cursor: pointer; }
        .file-btn { width: 50px; height: 50px; border: 2px solid #667eea; border-radius: 50%; background: white; color: #667eea; font-size: 1.4rem; cursor: pointer; }
        .file-input { display: none; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>Seguro Auto</h1>
            <p>Cotacao personalizada</p>
        </div>
        <div class="chat-messages" id="messages">
            <div class="message bot">Ola! Envie a foto do documento do seu veiculo clicando no botao de anexo.</div>
        </div>
        <div class="chat-input">
            <input type="file" id="fileInput" class="file-input" accept="image/*,.pdf">
            <button class="file-btn" onclick="document.getElementById('fileInput').click()">📎</button>
            <input type="text" id="userInput" placeholder="Digite...">
            <button onclick="sendMessage()">➤</button>
        </div>
    </div>
    <script>
        const messagesDiv = document.getElementById('messages');
        const userInput = document.getElementById('userInput');
        const fileInput = document.getElementById('fileInput');
        const sessionId = 'sess_' + Date.now();

        function addMessage(text, isUser) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : 'bot');
            div.textContent = text;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;
            addMessage(text, true);
            userInput.value = '';
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: text, session_id: sessionId})
            });
            const data = await response.json();
            addMessage(data.response, false);
        }

        async function uploadFile(file) {
            if (!file) return;
            addMessage('Enviando: ' + file.name, true);
            const formData = new FormData();
            formData.append('file', file);
            formData.append('session_id', sessionId);
            const response = await fetch('/upload', {method: 'POST', body: formData});
            const data = await response.json();
            addMessage(data.message, false);
        }

        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) uploadFile(file);
            fileInput.value = '';
        });

        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id', 'default')
    msg = data.get('message', '')
    
    if session_id not in conversations:
        conversations[session_id] = {"contact_info": {}, "awaiting_contact": False, "contact_step": 0}
    
    conv = conversations[session_id]
    
    # Handle contact collection
    if conv.get("awaiting_contact"):
        step = conv.get("contact_step", 0)
        if step == 0:
            conv["contact_info"]["name"] = msg
            conv["contact_step"] = 1
            return jsonify({"response": "Obrigado. Em qual cidade voce reside?"})
        elif step == 1:
            conv["contact_info"]["city"] = msg
            conv["awaiting_contact"] = False
            # Send to Telegram
            send_contact_info_to_telegram(session_id)
            return jsonify({"response": "Muito bem, " + msg + "! Todas as informacoes foram enviadas. Obrigado!"})
    
    # Greeting
    if 'oi' in msg.lower() or 'ola' in msg.lower():
        return jsonify({"response": "Ola! Envie a foto do documento do seu veiculo clicando no botao de anexo."})
    
    return jsonify({"response": "Nao entendi. Pode repetir?"})

@app.route('/upload', methods=['POST'])
def upload():
    session_id = request.form.get('session_id', 'default')
    
    if session_id not in conversations:
        conversations[session_id] = {"contact_info": {}, "awaiting_contact": False, "contact_step": 0}
    
    conv = conversations[session_id]
    
    if 'file' not in request.files:
        return jsonify({"message": "Nenhum arquivo."})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Arquivo vazio."})
    
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    file_data = file.read()
    
    success = False
    if ext in ['jpg', 'jpeg', 'png']:
        success = send_telegram_photo(file_data, "Documento recebido", filename)
    elif ext == 'pdf':
        success = send_telegram_document(file_data, "Documento recebido", filename)
    
    if success:
        if not conv.get("contact_info", {}).get("name"):
            conv["awaiting_contact"] = True
            conv["contact_step"] = 0
            return jsonify({"message": "Documento recebido! Qual seu nome completo?"})
        
        # If we already have name but not city
        if not conv.get("contact_info", {}).get("city"):
            return jsonify({"message": "Documento recebido! Qual sua cidade?"})
        
        # If we have both
        send_contact_info_to_telegram(session_id)
        return jsonify({"message": "Documento recebido! Todas informacoes ja foram enviadas."})
    
    return jsonify({"message": "Erro ao enviar."})

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
