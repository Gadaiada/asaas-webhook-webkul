from flask import Flask, request, jsonify
import requests
import os
import sys
import random
import string
from dotenv import load_dotenv

# 🔐 Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# 🔑 Configurações
CONFIG = {
    "WEBKUL_API_KEY": os.getenv("WEBKUL_API_KEY"),
    "ASAAS_API_KEY": os.getenv("ASAAS_API_KEY"),
    "CUSTOM_FIELD_ID": os.getenv("CUSTOM_FIELD_ID", "5734"),
    "CUSTOM_FIELD_VALUE": os.getenv("CUSTOM_FIELD_VALUE", "Assinatura Vendedor Mensal"),
    "DEFAULT_PHONE": os.getenv("DEFAULT_PHONE", "11999999999"),
    "DEFAULT_STATE": os.getenv("DEFAULT_STATE", "SP"),
    "DEFAULT_COUNTRY": os.getenv("DEFAULT_COUNTRY", "BR"),
    "ASAAS_API_URL": os.getenv("ASAAS_API_URL", "https://sandbox.asaas.com/api/v3"),
    "WEBKUL_API_URL": os.getenv("WEBKUL_API_URL", "https://mvmapi.webkul.com/api/v2")
}

# 🚨 Validação inicial
if not CONFIG["WEBKUL_API_KEY"] or not CONFIG["ASAAS_API_KEY"]:
    print("❌ ERRO: Variáveis de ambiente ausentes!")
    sys.exit(1)

# 🔧 Utilitários
def gerar_nome_loja():
    """Gera um nome de loja aleatório"""
    prefixos = ["Mega", "Super", "Prime", "Elite", "Gold"]
    sufixos = ["Store", "Shop", "Market", "Commerce"]
    return f"{random.choice(prefixos)}{random.choice(sufixos)}{random.randint(100,999)}"

def gerar_nome_vendedor():
    """Gera um nome de vendedor aleatório"""
    return f"Vendedor{random.randint(1000,9999)}"

def gerar_telefone():
    """Gera um telefone aleatório"""
    return f"11{random.randint(900000000, 999999999)}"

def log_webhook(data):
    """Registra dados do webhook"""
    print(f"🔔 Webhook Recebido - Evento: {data.get('event')}")
    print(f"📦 Payment ID: {data.get('payment', {}).get('id')}")
    print(f"👤 Customer ID: {data.get('payment', {}).get('customer')}")

# 🔄 Integração com APIs
class AsaasAPI:
    @staticmethod
    def get_customer(customer_id):
        url = f"{CONFIG['ASAAS_API_URL']}/customers/{customer_id}"
        headers = {"access_token": CONFIG["ASAAS_API_KEY"]}
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Erro ao buscar cliente: {response.status_code} - {response.text}")
            return None
        
        return response.json()

class WebkulAPI:
    @staticmethod
    def criar_vendedor(email):
    url = f"{CONFIG['WEBKUL_API_URL']}/sellers.json"
    headers = {
        "Authorization": f"Bearer {CONFIG['WEBKUL_API_KEY']}",
        "Content-Type": "application/json"
    }

    payload = {
        "sp_store_name": gerar_nome_loja(),
        "seller_name": gerar_nome_vendedor(),
        "email": email,
        "password": "12345",
        "state": CONFIG["DEFAULT_STATE"],
        "country": CONFIG["DEFAULT_COUNTRY"],
        "contact": gerar_telefone(),
        # Estrutura específica para planos Webkul:
        "seller_plan": {
            "id": "5734",  # ID do plano da sua imagem
            "name": "Assinatura Vendedor Mensal",  # Nome exato do plano
            "billing_period": "30days",  # Período do plano
            "price": "45.00"  # Preço (opcional)
        },
        "send_welcome_email": "0",
        "send_email_verification_link": "0"
    }

    print("📤 Payload completo:", json.dumps(payload, indent=2))
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ Vendedor criado com plano 5734")
        return True, response.json()
    
    print("❌ Erro na API:", response.text)
    return False, response.json()

# 🎯 Rota do Webhook (Corrigida)
@app.route("/webhook-asaas", methods=["POST"])
def webhook_handler():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400

        log_webhook(data)

        if data.get("event") != "PAYMENT_CONFIRMED":
            return jsonify({"status": "ignored"}), 200

        payment = data.get("payment", {})
        customer_id = payment.get("customer")
        
        if not customer_id:
            return jsonify({"error": "Customer ID ausente"}), 400

        customer = AsaasAPI.get_customer(customer_id)
        if not customer:
            return jsonify({"error": "Cliente não encontrado"}), 404

        email = customer.get("email")
        if not email:
            return jsonify({"error": "E-mail não encontrado"}), 400

        success, response = WebkulAPI.criar_vendedor(email)

        if success:
            return jsonify({
                "status": "success",
                "email": email,
                "senha": "12345",
                "data": response
            }), 200
        else:
            return jsonify({
                "status": "error",
                "error": "Falha ao criar vendedor",
                "details": response
            }), 422

    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {str(e)}")
        return jsonify({"error": "Erro interno"}), 500

# 🔥 Endpoint de Teste (REMOVA EM PRODUÇÃO)
@app.route("/teste-vendedor", methods=["GET", "POST"])
def teste_vendedor():
    try:
        email = request.json.get("email", "teste@exemplo.com") if request.method == "POST" else "teste@exemplo.com"
        
        success, response = WebkulAPI.criar_vendedor(email)
        
        if success:
            return jsonify({
                "status": "success",
                "email": email,
                "senha": "12345",
                "data": response
            }), 200
        else:
            return jsonify({
                "status": "error",
                "error": response
            }), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🏁 Health Check
@app.route("/")
def health_check():
    return jsonify({"status": "online", "service": "Asaas-Webkul"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
