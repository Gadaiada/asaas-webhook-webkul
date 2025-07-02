from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Configurações
WEBKUL_API_KEY = os.getenv("WEBKUL_API_KEY")
ASAAS_API_KEY = os.getenv("ASAAS_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")  # Adicione um segredo para validação

# Verificação inicial
if not all([WEBKUL_API_KEY, ASAAS_API_KEY, WEBHOOK_SECRET]):
    print("❌ ERRO: Variáveis de ambiente ausentes!")
    exit(1)

@app.route("/webhook-asaas", methods=["GET", "POST"])
def webhook_handler():
    # Verificação de saúde do endpoint (GET)
    if request.method == "GET":
        return jsonify({
            "status": "active",
            "service": "Asaas-Webkul Integration",
            "endpoint": "/webhook-asaas",
            "method": "POST"
        }), 200

    # Validação do segredo do webhook
    if request.headers.get('X-Webhook-Secret') != WEBHOOK_SECRET:
        return jsonify({"error": "Não autorizado"}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400

        # Processa apenas pagamentos confirmados
        if data.get("event") == "PAYMENT_CONFIRMED":
            payment = data.get("payment", {})
            customer_id = payment.get("customer")
            
            if not customer_id:
                return jsonify({"error": "Customer ID ausente"}), 400

            # Aqui viria a lógica de criação do vendedor
            return jsonify({"status": "success"}), 200

        return jsonify({"status": "ignored"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def health_check():
    return jsonify({
        "status": "online",
        "endpoints": {
            "/webhook-asaas": ["GET", "POST"],
            "/": ["GET"]
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
