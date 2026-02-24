# Car Insurance Lead Bot - Gustavo Melo - WITH DEBUG
from flask import Flask, render_template_string, request, jsonify
import requests
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '@Toustten')

conversations = {}

def send_telegram_photo(photo_data, caption, filename):
    if not TELEGRAM_BOT_TOKEN:
        print("[ERROR] No TELEGRAM_BOT_TOKEN for photo")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {'photo': (filename, photo_data, 'image/jpeg')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        print(f"[PHOTO] Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Photo failed: {e}")
        return False

def send_telegram_document(doc_data, caption, filename):
    if not TELEGRAM_BOT_TOKEN:
        print("[ERROR] No TELEGRAM_BOT_TOKEN for doc")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        files = {'document': (filename, doc_data, 'application/pdf')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data, timeout=30)
        print(f"[DOCUMENT] Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Document failed: {e}")
        return False

def send_final_summary(session_id):
    """Send ONE complete message with all info at the end"""
    print(f"[SUMMARY] Called for session {session_id[:10]}...")
    print(f"[SUMMARY] TOKEN present: {bool(TELEGRAM_BOT_TOKEN)}")
    print(f"[SUMMARY] CHAT_ID: {TELEGRAM_CHAT_ID}")
    
    if not TELEGRAM_BOT_TOKEN:
        print("[ERROR] No TELEGRAM_BOT_TOKEN!")
        return False
    
    conv = conversations.get(session_id, {})
    info = conv.get('info', {})
    docs = conv.get('docs', {})
    
    print(f"[SUMMARY] Info: {info}")
    print(f"[SUMMARY] Docs: {docs}")
    
    text = f"""🚗 NOVA COTACAO - GRUPO METZ

👤 NOME: {info.get('nome', '---')}
🏙️ CIDADE: {info.get('cidade', '---')}
🚗 VEICULO: {info.get('veiculo', '---')}
📞 TELEFONE: {info.get('telefone', '---')}

📎 DOCUMENTOS:
• Veiculo: {'SIM' if docs.get('doc_veiculo') else 'NAO'}
• CNH: {'SIM' if docs.get('cnh') else 'NAO'}

Sessao: {session_id[:10]}"""
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        print(f"[SUMMARY] Sending to {url}")
        print(f"[SUMMARY] Payload: {payload}")
        response = requests.post(url, json=payload, timeout=10)
        print(f"[SUMMARY] Response status: {response.status_code}")
        print(f"[SUMMARY] Response text: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Summary failed: {e}")
        return False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grupo Metz</title>
    <style>
        body { font-family: sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; margin: 0; }
        .chat-container { width: 100%; max-width: 420px; height: 85vh; background: white; border-radius: 24px; box-shadow: 0 25px 80px rgba(0,0,0,0.4); display: flex; flex-direction: column; overflow: hidden; }
        .chat-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; text-align: center; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 20px; }
        .message { max-width: 85%; padding: 14px 18px; border-radius: 20px; margin-bottom: 10px; font-size: 0.95rem; line-height: 1.4; }
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
            <h1>Grupo Metz</h1>
            <p>Protecao Veicular</p>
        </div>
        <div class="chat-messages" id="messages"></div>
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
            const response = await fetch('/chat', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: text, session_id: sessionId})});
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
        fileInput.addEventListener('change', (e) => { const file = e.target.files[0]; if (file) uploadFile(file); fileInput.value = ''; });
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        addMessage('Ola, tudo bem, sou o Gustavo Melo do grupo Metz, Protecao Veicular. Para estar fazendo sua cotacao, vou precisar de algumas informacoes.', false);
        setTimeout(() => addMessage('Para comecar, qual seu nome completo?', false), 500);
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
    msg = data.get('message', '').strip()
    print(f"[CHAT] Session: {session_id[:10]}, Message: {msg[:30]}")
    
    if session_id not in conversations:
        conversations[session_id] = {'step': 1, 'info': {}, 'docs': {}, 'completed': False}
    
    conv = conversations[session_id]
    step = conv['step']
    print(f"[CHAT] Current step: {step}")
    
    if conv.get('completed'):
        return jsonify({"response": "Obrigado! Sua cotacao ja foi enviada."})
    
    if step == 1:
        conv['info']['nome'] = msg
        conv['step'] = 2
        return jsonify({"response": "De qual cidade voce fala?"})
    
    elif step == 2:
        conv['info']['cidade'] = msg
        conv['step'] = 3
        return jsonify({"response": "Pra eu fazer uma cotacao mais exata, me informe a placa e o modelo do seu veiculo?"})
    
    elif step == 3:
        conv['info']['veiculo'] = msg
        conv['step'] = 4
        return jsonify({"response": "E tambem o telefone para contato."})
    
    elif step == 4:
        conv['info']['telefone'] = msg
        conv['step'] = 5
        return jsonify({"response": "Eu sei que ja pedi todas estas informacoes. Mas, poderia enviar uma foto ou copia do documento do veiculo? Clique no botao de anexo 📎."})
    
    elif step == 7:
        conv['step'] = 8
        return jsonify({"response": "Obrigado por todos estes detalhes, gostaria de acrescentar algo mais antes de eu comecar a trabalhar na sua cotacao?"})
    
    elif step == 8:
        print("[CHAT] Sending final summary...")
        conv['completed'] = True
        result = send_final_summary(session_id)
        print(f"[CHAT] Summary result: {result}")
        return jsonify({"response": "Perfeito! Vou preparar sua cotacao e entrar em contato em breve. Obrigado pela confianca!"})
    
    return jsonify({"response": "Aguardando documento... Clique no botao de anexo 📎."})

@app.route('/upload', methods=['POST'])
def upload():
    session_id = request.form.get('session_id', 'default')
    print(f"[UPLOAD] Session: {session_id[:10]}")
    
    if session_id not in conversations:
        conversations[session_id] = {'step': 0, 'info': {}, 'docs': {}, 'completed': False}
    
    conv = conversations[session_id]
    
    if conv.get('completed'):
        return jsonify({"message": "Sua cotacao ja foi enviada. Obrigado!"})
    
    if 'file' not in request.files:
        return jsonify({"message": "Nenhum arquivo enviado."})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Arquivo vazio."})
    
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    file_data = file.read()
    
    step = conv.get('step', 0)
    print(f"[UPLOAD] Step: {step}, File: {filename}")
    
    if step == 5:
        caption = f"📎 DOC VEICULO - {conv.get('info', {}).get('nome', 'Cliente')}"
        conv['docs']['doc_veiculo'] = True
        conv['step'] = 6
        
        success = False
        if ext in ['jpg', 'jpeg', 'png']:
            success = send_telegram_photo(file_data, caption, filename)
        elif ext == 'pdf':
            success = send_telegram_document(file_data, caption, filename)
        
        if success:
            return jsonify({"message": "Perfeito! Documento do veiculo recebido. Agora, se possivel, me envie uma foto da sua CNH tambem."})
        return jsonify({"message": "Ops, tive um problema ao receber o arquivo. Pode tentar enviar novamente?"})
    
    elif step == 6:
        caption = f"📎 CNH - {conv.get('info', {}).get('nome', 'Cliente')}"
        conv['docs']['cnh'] = True
        conv['step'] = 7
        
        success = False
        if ext in ['jpg', 'jpeg', 'png']:
            success = send_telegram_photo(file_data, caption, filename)
        elif ext == 'pdf':
            success = send_telegram_document(file_data, caption, filename)
        
        if success:
            return jsonify({"message": "Excelente! CNH recebida. Tem mais alguma informacao que gostaria de me passar antes de eu preparar sua cotacao?"})
        return jsonify({"message": "Ops, tive um problema ao receber o arquivo. Pode tentar enviar novamente?"})
    
    # Wrong step - be helpful not rude
    if step < 5:
        return jsonify({"message": "Obrigado pelo arquivo! Mas antes, preciso que voce responda as perguntas acima. Qual seu nome, cidade, veiculo e telefone?"})
    else:
        return jsonify({"message": "Obrigado! Estou processando suas informacoes."})

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
