from flask import Flask, request
import requests
import os
import sys
import random
import string
from dotenv import load_dotenv

# 🔐 Carrega variáveis do .env
load_dotenv()

app = Flask(__name__)

# 🔑 Variáveis de ambiente
WEBKUL_API_KEY = os.getenv("WEBKUL_API_KEY")
ASAAS_API_KEY = os.getenv("ASAAS_API_KEY")
CUSTOM_FIELD_ID = os.getenv("CUSTOM_FIELD_ID") or "5734"
CUSTOM_FIELD_VALUE = os.getenv("CUSTOM_FIELD_VALUE") or "Assinatura Vendedor Mensal"

# 🚨 Validação de variáveis obrigatórias
if not WEBKUL_API_KEY or not ASAAS_API_KEY:
    print("❌ ERRO: Variáveis de ambiente ausentes!")
    if not ASAAS_API_KEY:
        print("⚠️ Variável ASAAS_API_KEY não encontrada.")
    if not WEBKUL_API_KEY:
        print("⚠️ Variável WEBKUL_API_KEY não encontrada.")
    sys.exit(1)

# 🔐 Gera senha aleatória
def gerar_senha(tamanho=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=tamanho))

# 🔎 Buscar dados do cliente (ASAAS - sandbox)
def get_customer_data(customer_id):
    url = f"https://sandbox.asaas.com/api/v3/customers/{customer_id}"
    headers = {"access_token": ASAAS_API_KEY}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print("❌ Erro ao buscar cliente Asaas:", resp.status_code, resp.text)
        return {}

# 🔎 Buscar dados do pagamento (ASAAS - sandbox)
def get_payment_data(payment_id):
    url = f"https://sandbox.asaas.com/api/v3/payments/{payment_id}"
    headers = {"access_token": ASAAS_API_KEY}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print("❌ Erro ao buscar pagamento Asaas:", resp.status_code, resp.text)
        return {}

# 📥 Rota para receber eventos do Asaas
@app.route("/webhook-asaas", methods=["POST"])
def webhook():
    data = request.get_json()
    print("🚨 Webhook recebido do Asaas:", data)

    if data.get("event") == "PAYMENT_CONFIRMED":
        payment = data.get("payment", {})
        payment_id = payment.get("id")
        customer_raw = payment.get("customer")
        print("📦 Valor de payment['customer']:", customer_raw)

        customer = {}

        if isinstance(customer_raw, str):
            customer = get_customer_data(customer_raw)
        elif isinstance(customer_raw, dict):
            customer = customer_raw
        else:
            print("⚠️ 'customer' ausente ou inválido, buscando pelo payment_id...")
            payment_full = get_payment_data(payment_id)
            if payment_full:
                customer_id = payment_full.get("customer")
                if customer_id:
                    customer = get_customer_data(customer_id)

        # 🧾 Extrair dados do cliente
        nome = customer.get("name")
        email = customer.get("email")
        telefone = customer.get("phone") or "11999999999"

        # ⚠️ Verifica se os dados são válidos
        if not nome or not email:
            print("⚠️ Dados do cliente incompletos. Nome ou email ausente.")
            return "Cliente inválido", 400

        print(f"🛒 Criando vendedor: {nome}, {email}, {telefone}")
        criar_vendedor_webkul(nome, email, telefone)

    return "ok", 200

# 🧑‍💼 Criação do vendedor na Webkul
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
        "password": gerar_senha(),
        "state": "SP",
        "country": "Brasil",
        "contact": telefone,
        "custom_fields": [
    {
        "id": CUSTOM_FIELD_ID,
        "value": CUSTOM_FIELD_VALUE
    }
],

        "send_welcome_email": "1",
        "send_email_verification_link": "0"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("✅ Vendedor criado com sucesso.")
    else:
        print("❌ Erro ao criar vendedor Webkul:", response.status_code, response.text)


# ▶️ Iniciar app Flask
if __name__ == "__main__":
    print("✅ Ambiente validado com sucesso.")
    app.run(host="0.0.0.0", port=8000)
