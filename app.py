from flask import Flask, request, jsonify
import requests
import os
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
    "PLANO_ID": os.getenv("PLANO_ID", "5734"),
    "PLANO_NOME": os.getenv("PLANO_NOME", "Assinatura Vendedor Mensal"),
    "ESTADO_PADRAO": os.getenv("ESTADO_PADRAO", "SP"),
    "PAIS_PADRAO": os.getenv("PAIS_PADRAO", "BR"),
    "SENHA_PADRAO": os.getenv("SENHA_PADRAO", "12345"),
    "ASAAS_API_URL": os.getenv("ASAAS_API_URL", "https://sandbox.asaas.com/api/v3"),
    "WEBKUL_API_URL": os.getenv("WEBKUL_API_URL", "https://mvmapi.webkul.com/api/v2")
}

# Validação inicial
if not CONFIG["WEBKUL_API_KEY"]:
    print("❌ ERRO: Token do Webkul não configurado!")
    exit(1)

# Utilitários
def gerar_nome_loja(nome):
    """Gera nome da loja baseado no nome do cliente"""
    try:
        nome_base = nome.split()[0]
        return f"Loja {nome_base}{random.randint(100,999)}"
    except:
        return f"Loja Cliente{random.randint(1000,9999)}"

def validar_webhook(data):
    """Valida a estrutura do webhook"""
    required_fields = ['event', 'payment']
    if not all(field in data for field in required_fields):
        return False, "Campos obrigatórios faltando"
    
    if not isinstance(data.get('payment', {}), dict):
        return False, "Dados de pagamento inválidos"
    
    return True, ""

@app.route("/webhook-asaas", methods=["POST"])
def webhook_handler():
    try:
        # Verificação inicial
        if not request.is_json:
            return jsonify({"error": "Content-Type deve ser application/json"}), 415
        
        data = request.get_json()
        is_valid, msg = validar_webhook(data)
        
        if not is_valid:
            return jsonify({"error": msg}), 400

        print(f"🔔 Webhook recebido: {data.get('event')}")

        # Processa apenas pagamentos confirmados
        if data.get("event") != "PAYMENT_CONFIRMED":
            return jsonify({"status": "success", "message": "Evento não processado"}), 200

        payment = data.get("payment", {})
        customer_id = payment.get("customer")
        
        if not customer_id:
            return jsonify({"error": "Customer ID não encontrado"}), 400

        # Busca dados do cliente no Asaas
        headers = {"access_token": CONFIG["ASAAS_API_KEY"]}
        response = requests.get(f"{CONFIG['ASAAS_API_URL']}/customers/{customer_id}", headers=headers)
        
        if response.status_code != 200:
            return jsonify({"error": "Falha ao buscar cliente no Asaas"}), 400

        customer = response.json()
        nome = customer.get("name", "").strip()
        email = customer.get("email", "").strip()

        if not nome or not email:
            return jsonify({"error": "Nome ou e-mail do cliente ausentes"}), 400

        # Prepara dados para o Webkul
        payload = {
            "sp_store_name": gerar_nome_loja(nome),
            "seller_name": nome[:50],
            "email": email,
            "password": CONFIG["SENHA_PADRAO"],
            "state": CONFIG["ESTADO_PADRAO"],
            "country": CONFIG["PAIS_PADRAO"],
            "contact": f"11{random.randint(900000000, 999999999)}",
            "seller_plan": {
                "id": CONFIG["PLANO_ID"],
                "name": CONFIG["PLANO_NOME"]
            },
            "send_welcome_email": "0"
        }

        # Envia para Webkul
        headers = {
            "Authorization": f"Bearer {CONFIG['WEBKUL_API_KEY']}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{CONFIG['WEBKUL_API_URL']}/sellers.json",
            json=payload,
            headers=headers
        )

        if response.status_code == 200:
            return jsonify({
                "status": "success",
                "message": "Vendedor criado com sucesso"
            }), 200
        
        return jsonify({
            "status": "error",
            "error": "Falha ao criar vendedor",
            "details": response.text
        }), 422

    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)}")
        return jsonify({"error": "Erro interno no servidor"}), 500

@app.route("/")
def health_check():
    return jsonify({"status": "online"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
