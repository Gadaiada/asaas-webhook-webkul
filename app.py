from flask import Flask, request
import requests
import os
import sys

app = Flask(__name__)

# 🔐 Carregar variáveis de ambiente
WEBKUL_API_KEY = os.getenv("WEBKUL_API_KEY")
ASAAS_API_KEY = os.getenv("ASAAS_API_KEY")
CUSTOM_FIELD_ID = os.getenv("CUSTOM_FIELD_ID") or "5734"
CUSTOM_FIELD_VALUE = os.getenv("CUSTOM_FIELD_VALUE") or "Assinatura Vendedor Mensal"

# ✅ Validação de variáveis obrigatórias
if not WEBKUL_API_KEY or not ASAAS_API_KEY:
    print("❌ ERRO: Variáveis de ambiente ausentes!")
    if not ASAAS_API_KEY:
        print("⚠️ Variável ASAAS_API_KEY não encontrada.")
    if not WEBKUL_API_KEY:
        print("⚠️ Variável WEBKUL_API_KEY não encontrada.")
    sys.exit(1)  # Encerra o app com erro

def get_customer_data(customer_id):
    url = f"https://www.asaas.com/api/v3/customers/{customer_id}"
    headers = {"access_token": ASAAS_API_KEY}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print("❌ Erro ao buscar cliente Asaas:")
        print("Status:", resp.status_code)
        print("Motivo:", resp.text)
        return {}

def get_payment_data(payment_id):
    url = f"https://www.asaas.com/api/v3/payments/{payment_id}"
    headers = {"access_token": ASAAS_API_KEY}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print("❌ Erro ao buscar pagamento Asaas:")
        print("Status:", resp.status_code)
        print("Motivo:", resp.text)
        return {}

@app.route("/webhook-asaas", methods=["POST"])
def webhook():
    data = request.get_json()
    print("🚨 Webhook recebido do Asaas:", data)

    if data.get("event") == "PAYMENT_CONFIRMED":
        payment = data.get("payment", {})
        payment_id = payment.get("id")
        customer_raw = payment.get("customer", None)

        print("📦 Valor de payment['customer']:", customer_raw)

        customer = {}

        if isinstance(customer_raw, str):
            customer = get_customer_data(customer_raw)
        elif isinstance(customer_raw, dict):
            customer = customer_raw
        else:
            print("⚠️ 'customer' ausente ou inválido, buscando com payment_id...")
            payment_full = get_payment_data(payment_id)
            if payment_full:
                customer_id = payment_full.get("customer")
                if customer_id:
                    customer = get_customer_data(customer_id)

        nome = customer.get("name", "")
        email = customer.get("email", "")
        telefone = customer.get("phone", "") or "11999999999"

        print(f"🛒 Criando vendedor: {nome}, {email}, {telefone}")
        criar_vendedor_webkul(nome, email, telefone)

    return "ok", 200

def criar_vendedor_webkul(nome, email, telefone):
    url = "https://mvmapi.webkul.com/api/v2/sellers.json"
    headers = {
        "Authorization": f"Bearer {WEBKUL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "sp_store_name": f"Loja de {nome}",
        "seller_name": nome,
        "email": email,
        "password": "senha12345",
        "state": "SP",
        "country": "Brasil",
        "contact": telefone,
        "custom_fields": [
            {CUSTOM_FIELD_ID: CUSTOM_FIELD_VALUE}
        ],
        "send_welcome_email": "1",
        "send_email_verification_link": "0"
    }

    response = requests.post(url, json=payload, headers=headers)
    print("📬 Resposta Webkul:", response.status_code, response.text)

if __name__ == "__main__":
    print("✅ Ambiente validado com sucesso.")
    app.run(host="0.0.0.0", port=8000)
