# Car Insurance Lead Bot - Deployment Ready
# Environment variables: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

from flask import Flask, render_template_string, request, jsonify
import requests
import os

app = Flask(__name__)

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '@Toustten')

# Knowledge base
KNOWLEDGE = {
    "greetings": ["oi", "olá", "ola", "e aí", "e ai", "tudo bem", "bom dia", "boa tarde", "boa noite", "hey", "hi", "hello"],
    
    "insurance_types": {
        "responsabilidade": "Responsabilidade Civil (RC) cobre danos a terceiros. É obrigatória no Brasil. Cobre danos materiais e corporais que você causar a outras pessoas.",
        "civil": "Responsabilidade Civil (RC) cobre danos a terceiros. É obrigatória no Brasil.",
        "rc": "Responsabilidade Civil (RC) cobre danos a terceiros. É obrigatória no Brasil.",
        "colisão": "Seguro de Colisão cobre danos ao seu próprio veículo em caso de acidente, independente de quem tenha causado.",
        "colisao": "Seguro de Colisão cobre danos ao seu próprio veículo em caso de acidente, independente de quem tenha causado.",
        "ambos": "Temos os dois tipos: Responsabilidade Civil (obrigatória, cobre terceiros) e Colisão (cobre seu carro). Quer saber mais sobre algum?",
        "os dois": "Temos os dois tipos: Responsabilidade Civil (obrigatória, cobre terceiros) e Colisão (cobre seu carro)."
    },
    
    "requirements": "Para fazer o seguro precisamos de: CNH válida e documento do veículo (CRLV). O processo é rápido!",
    
    "claims": "Para acionar o sinistro, ligue para 0800 090 090. Atendimento 24h.",
    
    "coverage_area": "Atendemos em todo o território brasileiro! 🚗🇧🇷",
    
    "pricing": "Vou te fazer algumas perguntas rápidas para preparar sua cotação personalizada.",
    
    "quote_questions": {
        "vehicle": "Qual o veículo? (marca, modelo e ano)",
        "coverage": "Qual cobertura deseja?\n• Responsabilidade Civil (cobre terceiros)\n• Colisão (cobre seu carro)\n• Os dois",
        "location": "Em qual cidade/estado fica o veículo?",
        "driver_age": "Qual a idade do motorista principal?"
    },
    
    "opening_message": "Tudo bem? 😊\n\nEu imagino que você veio para cotação de seguro. Se for isso, posso te fazer umas perguntas para cotação?\n\nOu se preferir, posso te ajudar com:\n• Tipos de seguro (RC ou colisão)\n• Documentos necessários\n• Sinistros",
    
    "fallback_responses": [
        "Hmm, não entendi direito. Posso te ajudar com: tipos de seguro (RC ou colisão), documentos necessários, ou cotação. O que precisa?",
        "Desculpe, não captei. Trabalhamos com seguro de Responsabilidade Civil e Colisão para todo o Brasil. Como posso ajudar?"
    ]
}

# Conversation state (simple in-memory, resets on restart)
conversations = {}

def send_telegram_alert(title, details):
    """Send escalation alert to Telegram"""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == '':
        print(f"[TELEGRAM NOT CONFIGURED] Would send: {title}")
        return
    
    text = f"🚨 <b>{title}</b>\n\n{details}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"Telegram alert sent: {response.status_code}")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def send_quote_summary(session_id):
    """Send complete quote info to Telegram"""
    conv = conversations.get(session_id, {})
    quote_data = conv.get('quote_data', {})
    
    details = f"""
<b>🚗 NOVA COTAÇÃO DE SEGURO</b>

<b>Veículo:</b> {quote_data.get('vehicle', 'Não informado')}
<b>Cobertura:</b> {quote_data.get('coverage', 'Não informado')}
<b>Localização:</b> {quote_data.get('location', 'Não informado')}
<b>Idade do motorista:</b> {quote_data.get('driver_age', 'Não informado')}

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
            "quote_data": {}
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
        
        # Ask next question or finish
        if quote_step < len(quote_questions):
            next_question = quote_questions[quote_step]
            conv["quote_step"] = quote_step + 1
            return KNOWLEDGE_BASE["quote_questions"][next_question]
        else:
            # All questions answered
            conv["in_quote_flow"] = False
            conv["quote_step"] = 0
            send_quote_summary(session_id)
            return "Perfeito! Enviei todas as informações para nosso consultor. Ele vai preparar sua cotação e entrar em contato em breve! 🚗✅\n\nAlguma outra dúvida?"
    
    # Check for greetings or first message
    if any(greet in msg_lower for greet in KNOWLEDGE_BASE["greetings"]) and conv["step"] == "greeting":
        conv["step"] = "menu"
        return KNOWLEDGE_BASE["opening_message"]
    
    # Check for quote request
    if any(word in msg_lower for word in ["preço", "preco", "valor", "cotação", "cotacao", "quanto custa", "quote", "orçamento", "orcamento", "quanto fica", "fazer seguro", "cotar", "sim", "pode ser", "quero"]):
        conv["in_quote_flow"] = True
        conv["quote_step"] = 0
        conv["quote_data"] = {}
        return KNOWLEDGE_BASE["pricing"] + "\n\n" + KNOWLEDGE_BASE["quote_questions"]["vehicle"]
    
    # Check for insurance types
    for key, response in KNOWLEDGE_BASE["insurance_types"].items():
        if key in msg_lower:
            conv["step"] = "details"
            return response + "\n\nQuer fazer uma cotação?"
    
    # Check for requirements
    if any(word in msg_lower for word in ["documento", "documentos", "precisa", "cnh", "requerimento", "requirements", "preciso de"]):
        return KNOWLEDGE_BASE["requirements"] + "\n\nQuer fazer uma cotação?"
    
    # Check for claims/sinister
    if any(word in msg_lower for word in ["sinistro", "acidente", "bateu", "bati", "roubaram", "furto", "claim", "0800", "bater"]):
        return KNOWLEDGE_BASE["claims"]
    
    # Check for coverage area
    if any(word in msg_lower for word in ["onde", "cidade", "estado", "brasil", "cobertura", "área", "area", "atende", "funciona"]):
        return KNOWLEDGE_BASE["coverage_area"]
    
    # Check for no/exit responses
    if msg_lower in ["não", "nao", "no", "obrigado", "valeu", "flw", "tchau"]:
        return "Sem problemas! Se precisar de algo é só chamar. 👍"
    
    # Unknown input — escalate after 2 failures
    conv["unknown_count"] += 1
    
    if conv["unknown_count"] >= 2:
        send_telegram_alert("Cliente não entendido", f"Mensagem: {user_message}")
        conv["unknown_count"] = 0
        return "Desculpe, não estou conseguindo entender direito. Vou chamar um consultor para te ajudar! Aguarde um momento... 🔄"
    
    return KNOWLEDGE_BASE["fallback_responses"][conv["unknown_count"] - 1]
    # HTML template for the chat interface
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
        .chat-input {
            padding: 18px 20px;
            border-top: 1px solid #e8e8e8;
            display: flex;
            gap: 12px;
            background: #fafafa;
        }
        .chat-input input {
            flex: 1;
            padding: 14px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 28px;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.3s;
            background: white;
        }
        .chat-input input:focus {
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
            <p>Cotação rápida | Atendimento 24h | Todo Brasil</p>
        </div>
        <div class="chat-messages" id="messages">
            <div class="message bot">Tudo bem? 😊<br><br>Eu imagino que você veio para cotação de seguro. Se for isso, posso te fazer umas perguntas para cotação?<br><br>Ou se preferir, posso te ajudar com:<br>• Tipos de seguro (RC ou colisão)<br>• Documentos necessários<br>• Sinistros</div>
        </div>
        <div class="typing" id="typing">
            <span></span><span></span><span></span>
        </div>
        <div class="chat-input">
            <input type="text" id="userInput" placeholder="Digite sua mensagem..." autocomplete="off">
            <button onclick="sendMessage()">➤</button>
        </div>
        <div class="footer">Protegido por criptografia 🔒</div>
    </div>

    <script>
        const messagesDiv = document.getElementById('messages');
        const userInput = document.getElementById('userInput');
        const typingDiv = document.getElementById('typing');
        const sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

        function addMessage(text, isUser) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : 'bot');
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
                addMessage('Desculpe, tive um problema. Tente novamente!', false);
            }
        }

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

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
