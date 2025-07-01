from flask import Flask, request, jsonify
import requests
import os
import sys
import random
import string
from dotenv import load_dotenv

# 🔐 Carrega variáveis do .env
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
def gerar_senha(tamanho=12):
    """Gera senha aleatória segura"""
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    return ''.join([random.choice(caracteres) for _ in range(tamanho)])

def formatar_telefone(numero):
    """Remove formatação do telefone"""
    return ''.join(filter(str.isdigit, str(numero)))[:15] or CONFIG["DEFAULT_PHONE"]

def log_webhook(data):
    """Registra dados do webhook para debug"""
    print(f"🔔 Webhook Recebido: {data.get('event')}")
    print(f"📦 Payment ID: {data.get('payment', {}).get('id')}")
    print(f"👤 Customer ID: {data.get('payment', {}).get('customer')}")

# 🔄 Integração com APIs
class AsaasAPI:
    @staticmethod
    def get_customer(customer_id):
        url = f"{CONFIG['ASAAS_API_URL']}/customers/{customer_id}"
        headers = {"access_token": CONFIG["ASAAS_API_KEY"]}
        response = requests.get(url, headers=headers)
        return response.json() if response.status_code == 200 else None

    @staticmethod
    def get_payment(payment_id):
        url = f"{CONFIG['ASAAS_API_URL']}/payments/{payment_id}"
        headers = {"access_token": CONFIG["ASAAS_API_KEY"]}
        response = requests.get(url, headers=headers)
        return response.json() if response.status_code == 200 else None

class WebkulAPI:
    @staticmethod
    def criar_vendedor(nome, email, telefone):
        url = f"{CONFIG['WEBKUL_API_URL']}/sellers.json"
        headers = {
            "Authorization": f"Bearer {CONFIG['WEBKUL_API_KEY']}",
            "Content-Type": "application/json"
        }

        payload = {
            "sp_store_name": f"Loja {nome[:20]}".strip(),
            "seller_name": nome[:50].strip(),
            "email": email,
            "password": gerar_senha(),
            "state": CONFIG["DEFAULT_STATE"],
            "country": CONFIG["DEFAULT_COUNTRY"],
            "contact": formatar_telefone(telefone),
            "custom_fields": {
                CONFIG["CUSTOM_FIELD_ID"]: CONFIG["CUSTOM_FIELD_VALUE"]
            },
            "send_welcome_email": "0",
            "send_email_verification_link": "0"
        }

        print(f"📤 Enviando payload para Webkul: {payload}")  # Log para debug
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            print("✅ Vendedor criado com sucesso.")
            return True, response.json()
        else:
            print(f"❌ Erro {response.status_code} ao criar vendedor: {response.text}")
            return False, response.json()

# 🎯 Rota do Webhook - Corrigida para /webhook-asaas
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

        # Busca dados do cliente
        customer = AsaasAPI.get_customer(customer_id)
        if not customer:
            return jsonify({"error": "Cliente não encontrado"}), 404

        # Valida dados mínimos
        if not all([customer.get("name"), customer.get("email")]):
            return jsonify({"error": "Dados do cliente incompletos"}), 400

        # Cria vendedor no Webkul
        success, response = WebkulAPI.criar_vendedor(
            nome=customer["name"],
            email=customer["email"],
            telefone=customer.get("phone", "")
        )

        if success:
            return jsonify({"status": "success", "data": response}), 200
        else:
            return jsonify({"status": "error", "details": response}), 422

    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        return jsonify({"error": "Erro interno do servidor"}), 500

# 🏁 Health Check
@app.route("/")
def health_check():
    return jsonify({
        "status": "online",
        "service": "Asaas-Webkul Webhook",
        "version": "1.0.1"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
