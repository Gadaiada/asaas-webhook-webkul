from flask import Flask, request, jsonify
import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configurações
CONFIG = {
    "WEBKUL_API_KEY": os.getenv("WEBKUL_API_KEY"),
    "ASAAS_API_KEY": os.getenv("ASAAS_API_KEY"),
    "WEBHOOK_SECRET": os.getenv("WEBHOOK_SECRET"),
    "PLANO_ID": os.getenv("PLANO_ID", "5734"),
    "PLANO_NOME": os.getenv("PLANO_NOME", "Assinatura Vendedor Mensal"),
    "ESTADO_PADRAO": os.getenv("ESTADO_PADRAO", "SP"),
    "PAIS_PADRAO": os.getenv("PAIS_PADRAO", "BR"),
    "SENHA_PADRAO": os.getenv("SENHA_PADRAO", "12345")
}

# Schema de validação para o webhook
WEBHOOK_SCHEMA = {
    "type": "object",
    "required": ["event", "payment"],
    "properties": {
        "event": {"type": "string"},
        "payment": {
            "type": "object",
            "required": ["customer", "value", "status"],
            "properties": {
                "customer": {"type": "string"},
                "value": {"type": "number"},
                "status": {"type": "string"}
            }
        }
    }
}

def validate_json(data, schema):
    """Valida o JSON contra um schema especificado"""
    errors = []
    
    # Verifica campos obrigatórios
    for field in schema.get('required', []):
        if field not in data:
            errors.append(f"Campo obrigatório faltando: {field}")
    
    # Verifica tipos dos campos
    for field, props in schema.get('properties', {}).items():
        if field in data:
            if not isinstance(data[field], props['type']):
                errors.append(f"Campo {field} deve ser do tipo {props['type'].__name__}")
    
    return errors

@app.route("/webhook-asaas", methods=["POST"])
def webhook_handler():
    # Verificação inicial do cabeçalho
    if not request.is_json:
        return jsonify({
            "error": "Content-Type inválido",
            "message": "O cabeçalho Content-Type deve ser application/json"
        }), 400
    
    # Verificação do segredo do webhook
    if request.headers.get('X-Webhook-Secret') != CONFIG['WEBHOOK_SECRET']:
        return jsonify({
            "error": "Não autorizado",
            "message": "Secret do webhook inválido"
        }), 401
    
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({
            "error": "JSON inválido",
            "message": str(e)
        }), 400
    
    # Validação contra o schema
    validation_errors = validate_json(data, WEBHOOK_SCHEMA)
    if validation_errors:
        return jsonify({
            "error": "Dados inválidos",
            "details": validation_errors,
            "expected_format": WEBHOOK_SCHEMA
        }), 400
    
    # Processamento específico para pagamentos confirmados
    if data['event'] == 'PAYMENT_CONFIRMED':
        payment = data['payment']
        
        # Validações adicionais para pagamentos
        if payment['status'] != 'CONFIRMED':
            return jsonify({
                "error": "Status de pagamento inválido",
                "message": "Apenas pagamentos CONFIRMED são processados"
            }), 400
        
        if payment['value'] <= 0:
            return jsonify({
                "error": "Valor de pagamento inválido",
                "message": "O valor do pagamento deve ser positivo"
            }), 400
        
        # Aqui você adicionaria a lógica para criar o vendedor
        try:
            # Exemplo: buscar dados do cliente no Asaas
            customer_url = f"https://api.asaas.com/v3/customers/{payment['customer']}"
            headers = {"access_token": CONFIG["ASAAS_API_KEY"]}
            response = requests.get(customer_url, headers=headers)
            
            if response.status_code != 200:
                return jsonify({
                    "error": "Falha ao buscar cliente",
                    "details": response.json()
                }), 400
            
            customer_data = response.json()
            
            # Simulação de criação do vendedor
            vendedor = {
                "nome": customer_data.get('name', 'Novo Vendedor'),
                "email": customer_data['email'],
                "data_criacao": datetime.now().isoformat(),
                "status": "ativo"
            }
            
            return jsonify({
                "status": "success",
                "vendedor": vendedor
            }), 200
            
        except Exception as e:
            return jsonify({
                "error": "Erro ao processar pagamento",
                "message": str(e)
            }), 500
    
    return jsonify({"status": "ignored"}), 200

@app.route("/")
def health_check():
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
