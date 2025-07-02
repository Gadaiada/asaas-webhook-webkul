from flask import Flask, request, jsonify
import requests
import os
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
    "PLANO_ID": os.getenv("PLANO_ID", "5734"),  # ID do plano de assinatura
    "PLANO_NOME": os.getenv("PLANO_NOME", "Assinatura Vendedor Mensal"),
    "ESTADO_PADRAO": os.getenv("ESTADO_PADRAO", "SP"),
    "PAIS_PADRAO": os.getenv("PAIS_PADRAO", "BR"),
    "SENHA_PADRAO": os.getenv("SENHA_PADRAO", "12345"),  # Senha temporária
    "ASAAS_API_URL": os.getenv("ASAAS_API_URL", "https://sandbox.asaas.com/api/v3"),
    "WEBKUL_API_URL": os.getenv("WEBKUL_API_URL", "https://mvmapi.webkul.com/api/v2")
}

# 🚨 Validação inicial
if not CONFIG["WEBKUL_API_KEY"] or not CONFIG["ASAAS_API_KEY"]:
    print("❌ ERRO: Variáveis de ambiente ausentes!")
    exit(1)

# 🔧 Utilitários
def gerar_nome_loja(nome_cliente):
    """Gera um nome de loja baseado no nome do cliente"""
    nome_base = nome_cliente.split()[0].title()  # Pega o primeiro nome
    sufixos = ["Store", "Shop", "Market", "Comércio"]
    return f"Loja {nome_base}{random.choice(sufixos)}{random.randint(10,99)}"

def gerar_telefone():
    """Gera um número de telefone aleatório válido"""
    return f"11{random.randint(900000000, 999999999)}"

def log_webhook(data):
    """Registra os dados do webhook"""
    print(f"🔔 Webhook Recebido - Evento: {data.get('event')}")
    print(f"📦 ID Pagamento: {data.get('payment', {}).get('id')}")
    print(f"👤 Cliente: {data.get('payment', {}).get('customer')}")

# 🔄 Integração com APIs
class AsaasAPI:
    @staticmethod
    def buscar_cliente(customer_id):
        """Busca dados do cliente no Asaas"""
        url = f"{CONFIG['ASAAS_API_URL']}/customers/{customer_id}"
        headers = {"access_token": CONFIG["ASAAS_API_KEY"]}
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Erro ao buscar cliente: {response.status_code} - {response.text}")
            return None
        
        return response.json()

class WebkulAPI:
    @staticmethod
    def criar_vendedor(nome, email):
        """Cria um novo vendedor no Webkul com configurações padrão"""
        url = f"{CONFIG['WEBKUL_API_URL']}/sellers.json"
        headers = {
            "Authorization": f"Bearer {CONFIG['WEBKUL_API_KEY']}",
            "Content-Type": "application/json"
        }

        payload = {
            "sp_store_name": gerar_nome_loja(nome),
            "seller_name": nome[:50],  # Limita o tamanho do nome
            "email": email,
            "password": CONFIG["SENHA_PADRAO"],
            "state": CONFIG["ESTADO_PADRAO"],
            "country": CONFIG["PAIS_PADRAO"],
            "contact": gerar_telefone(),
            "seller_plan": {
                "id": CONFIG["PLANO_ID"],
                "name": CONFIG["PLANO_NOME"],
                "billing_period": "30days"
            },
            "send_welcome_email": "1",  # Habilita e-mail de boas-vindas
            "send_email_verification_link": "0"
        }

        print(f"📤 Dados do vendedor sendo enviados:\n{json.dumps(payload, indent=2)}")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            print("✅ Vendedor criado com sucesso!")
            return True, response.json()
        
        print(f"❌ Falha ao criar vendedor: {response.status_code} - {response.text}")
        return False, response.json()

# 🎯 Rota Principal do Webhook
@app.route("/webhook-asaas", methods=["POST"])
def webhook_handler():
    try:
        # Verifica se há dados JSON
        if not request.is_json:
            return jsonify({"error": "Dados não fornecidos em formato JSON"}), 400

        data = request.get_json()
        log_webhook(data)

        # Verifica se é um pagamento confirmado
        if data.get("event") != "PAYMENT_CONFIRMED":
            return jsonify({"status": "ignored", "reason": "evento_nao_suportado"}), 200

        payment = data.get("payment", {})
        customer_id = payment.get("customer")
        
        if not customer_id:
            return jsonify({"error": "ID do cliente não encontrado"}), 400

        # Busca dados completos do cliente
        cliente = AsaasAPI.buscar_cliente(customer_id)
        if not cliente:
            return jsonify({"error": "Cliente não encontrado no Asaas"}), 404

        nome = cliente.get("name", "").strip()
        email = cliente.get("email", "").strip()

        if not nome or not email:
            return jsonify({"error": "Nome ou e-mail do cliente ausente"}), 400

        # Cria o vendedor no Webkul
        sucesso, resposta = WebkulAPI.criar_vendedor(nome, email)

        if sucesso:
            return jsonify({
                "status": "success",
                "email": email,
                "senha_temporaria": CONFIG["SENHA_PADRAO"],
                "detalhes": resposta
            }), 200
        else:
            return jsonify({
                "status": "error",
                "error": "Falha ao criar vendedor",
                "detalhes": resposta
            }), 422

    except Exception as e:
        print(f"❌ ERRO INESPERADO: {str(e)}")
        return jsonify({"error": "Erro interno no servidor"}), 500

# 🏁 Health Check
@app.route("/")
def health_check():
    return jsonify({
        "status": "online",
        "servico": "Integração Asaas-Webkul",
        "versao": "2.0"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
