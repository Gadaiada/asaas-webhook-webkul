from flask import Flask, request, jsonify
import requests
import os
import random
import string
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Configurações
CONFIG = {
    "WEBKUL_API_KEY": os.getenv("WEBKUL_API_KEY"),
    "ASAAS_API_KEY": os.getenv("ASAAS_API_KEY"),
    "CUSTOM_FIELD_ID": os.getenv("CUSTOM_FIELD_ID", "5734"),
    "CUSTOM_FIELD_VALUE": os.getenv("CUSTOM_FIELD_VALUE", "Assinatura Vendedor Mensal"),
    "DEFAULT_STATE": os.getenv("DEFAULT_STATE", "SP"),
    "DEFAULT_COUNTRY": os.getenv("DEFAULT_COUNTRY", "BR")
}

# Validação inicial
if not CONFIG["WEBKUL_API_KEY"]:
    print("❌ ERRO: Token do Webkul não configurado!")
    sys.exit(1)

# Utilitários
def gerar_nome_loja():
    prefixos = ["Mega", "Super", "Top", "Prime", "Elite"]
    sufixos = ["Store", "Shop", "Commerce", "Market"]
    return f"{random.choice(prefixos)}{random.choice(sufixos)}{random.randint(100,999)}"

def gerar_telefone():
    return f"11{random.randint(900000000, 999999999)}"

class WebkulAPI:
    @staticmethod
    def criar_vendedor(email):
        url = "https://mvmapi.webkul.com/api/v2/sellers.json"
        headers = {
            "Authorization": f"Bearer {CONFIG['WEBKUL_API_KEY']}",
            "Content-Type": "application/json"
        }

        payload = {
            "sp_store_name": gerar_nome_loja(),
            "seller_name": f"Vendedor{random.randint(1000,9999)}",
            "email": email,
            "password": "12345",  # Senha fixa
            "state": CONFIG["DEFAULT_STATE"],
            "country": CONFIG["DEFAULT_COUNTRY"],
            "contact": gerar_telefone(),
            "custom_fields": {
                CONFIG["CUSTOM_FIELD_ID"]: CONFIG["CUSTOM_FIELD_VALUE"]
            },
            "send_welcome_email": "0",
            "send_email_verification_link": "0"
        }

        print(f"🔧 Payload de teste: {payload}")  # Log detalhado
        response = requests.post(url, json=payload, headers=headers)
        
        return response.status_code == 200, response.json()

# Rota de teste - REMOVA EM PRODUÇÃO
@app.route("/teste-vendedor", methods=["GET", "POST"])
def teste_vendedor():
    try:
        # Teste com e-mail padrão ou recebido via POST
        email_teste = request.json.get("email", "teste@exemplo.com") if request.method == "POST" else "teste@exemplo.com"
        
        success, resposta = WebkulAPI.criar_vendedor(email_teste)
        
        if success:
            return jsonify({
                "status": "success",
                "email": email_teste,
                "senha": "12345",
                "dados": resposta
            }), 200
        else:
            return jsonify({
                "status": "error",
                "codigo": resposta.get("status_code"),
                "erro": resposta.text if hasattr(resposta, 'text') else str(resposta)
            }), 400

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# Rota principal do webhook
@app.route("/webhook-asaas", methods=["POST"])
def webhook_handler():
    # ... (implementação existente do webhook) ...
    pass

@app.route("/")
def health_check():
    return jsonify({"status": "online", "service": "Asaas-Webkul"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
