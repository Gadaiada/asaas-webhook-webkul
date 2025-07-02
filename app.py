from flask import Flask, request, jsonify
import requests
import os
import sys
import random
import json
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
    "DEFAULT_PHONE": os.getenv("DEFAULT_PHONE", "11999999999"),
    "DEFAULT_STATE": os.getenv("DEFAULT_STATE", "SP"),
    "DEFAULT_COUNTRY": os.getenv("DEFAULT_COUNTRY", "BR"),
    "ASAAS_API_URL": os.getenv("ASAAS_API_URL", "https://sandbox.asaas.com/api/v3"),
    "WEBKUL_API_URL": os.getenv("WEBKUL_API_URL", "https://mvmapi.webkul.com/api/v2")
}

# Validação inicial
if not CONFIG["WEBKUL_API_KEY"] or not CONFIG["ASAAS_API_KEY"]:
    print("❌ ERRO: Variáveis de ambiente ausentes!")
    sys.exit(1)

# Utilitários
def gerar_nome_loja():
    return f"Loja{random.randint(1000,9999)}"

def gerar_nome_vendedor():
    return f"Vendedor{random.randint(1000,9999)}"

def gerar_telefone():
    return f"11{random.randint(900000000, 999999999)}"

# Integração com APIs
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

    @staticmethod
    def get_customer_by_payment_id(payment_id):
        url = f"{CONFIG['ASAAS_API_URL']}/payments/{payment_id}"
        headers = {"access_token": CONFIG["ASAAS_API_KEY"]}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"❌ Erro ao buscar pagamento: {response.status_code} - {response.text}")
            return None

        payment_data = response.json()
        customer_id = payment_data.get("customer")
        if not customer_id:
            print("❌ Nenhum customer_id encontrado no pagamento.")
            return None

        return AsaasAPI.get_customer(customer_id)

class WebkulAPI:
    @staticmethod
    def criar_vendedor(email, nome):
        url = f"{CONFIG['WEBKUL_API_URL']}/sellers.json"
        headers = {
            "Authorization": f"Bearer {CONFIG['WEBKUL_API_KEY']}",
            "Content-Type": "application/json"
        }

        payload = {
            "sp_store_name": gerar_nome_loja(),
            "seller_name": nome or gerar_nome_vendedor(),
            "email": email,
            "password": "1234",  # Senha provisória
            "state": CONFIG["DEFAULT_STATE"],
            "country": CONFIG["DEFAULT_COUNTRY"],
            "contact": gerar_telefone(),
            "seller_plan": {
                "id": CONFIG["CUSTOM_FIELD_ID"],
                "name": CONFIG["CUSTOM_FIELD_VALUE"],
                "billing_period": "30days",
                "price": "45.00"
            },
            "send_welcome_email": "0",
            "send_email_verification_link": "0"
        }

        print(f"📤 Enviando para Webkul: {json.dumps(payload, indent=2)}")
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            print("✅ Vendedor criado com sucesso!")
            return True, response.json()

        print(f"❌ Falha na criação do vendedor: {response.status_code} - {response.text}")
        return False, response.text

# Webhook Asaas
@app.route("/webhook-asaas", methods=["POST"])
def webhook_handler():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados ausentes"}), 400

        print("🔔 Webhook recebido:", data.get("event"))

        if data.get("event") != "PAYMENT_CONFIRMED":
            return jsonify({"status": "ignorado"}), 200

        payment = data.get("payment", {})
        customer_id = payment.get("customer")

        # Fallback se customer vier nulo
        if customer_id:
            customer = AsaasAPI.get_customer(customer_id)
        else:
            payment_id = payment.get("id")
            print("⚠️ Customer ID ausente. Buscando por payment_id:", payment_id)
            customer = AsaasAPI.get_customer_by_payment_id(payment_id)

        if not customer:
            return jsonify({"error": "Cliente não encontrado"}), 404

        nome = customer.get("name", "")
        email = customer.get("email", "")
        if not email:
            return jsonify({"error": "E-mail não disponível"}), 400

        sucesso, resposta = WebkulAPI.criar_vendedor(email=email, nome=nome)

        if sucesso:
            return jsonify({
                "status": "vendedor_criado",
                "email": email,
                "senha": "1234",
                "resposta": resposta
            }), 200
        else:
            return jsonify({
                "status": "erro",
                "mensagem": resposta
            }), 422

    except Exception as e:
        print(f"❌ Erro geral no webhook: {str(e)}")
        return jsonify({"error": "Erro interno"}), 500

# Health check
@app.route("/")
def status():
    return jsonify({"status": "online"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
