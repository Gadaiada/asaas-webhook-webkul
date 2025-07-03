from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# -------------------------------------------------
# Configurações carregadas do .env (com valores padrão)
# -------------------------------------------------
CONFIG = {
    "WEBKUL_API_KEY": os.getenv("WEBKUL_API_KEY"),
    "ASAAS_API_KEY": os.getenv("ASAAS_API_KEY"),
    "WEBHOOK_SECRET": os.getenv("WEBHOOK_SECRET"),
    "PLANO_ID": os.getenv("PLANO_ID", "5734"),
    "PLANO_NOME": os.getenv("PLANO_NOME", "Assinatura Vendedor Mensal"),
    "ESTADO_PADRAO": os.getenv("ESTADO_PADRAO", "SP"),
    "PAIS_PADRAO": os.getenv("PAIS_PADRAO", "BR"),
    "SENHA_PADRAO": os.getenv("SENHA_PADRAO", "12345"),
}

# -------------------------------------------------
# JSON Schema simplificado para o payload do Asaas
# (formato inspirado em JSON‑Schema Draft‑07)
# -------------------------------------------------
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
                "status": {"type": "string"},
            },
        },
    },
}

# --------------------------------------------------------------------
# Função de validação mínima (recursiva) baseada no schema acima
# --------------------------------------------------------------------

def validate_json(data: dict, schema: dict, path: str = "") -> list[str]:
    """Valida um dicionário Python contra um schema minimalista.
    Retorna lista de strings de erro (vazia se estiver válido)."""

    # Mapeia tipos do schema (string) para tipos Python reais
    TYPE_MAP: dict[str, tuple | type] = {
        "string": str,
        "number": (int, float),
        "object": dict,
        "array": list,
        "boolean": bool,
        "null": type(None),
    }

    errors: list[str] = []

    # 1. Campos obrigatórios de nível atual
    required_fields = schema.get("required", [])
    for field in required_fields:
        if field not in data:
            errors.append(f"{path}{field}: campo obrigatório ausente")

    # 2. Propriedades declaradas
    properties = schema.get("properties", {})
    for field, props in properties.items():
        if field not in data:
            # Se não veio no payload, já foi tratado em "required" (se aplicável)
            continue

        expected_type = TYPE_MAP.get(props["type"])
        actual_value = data[field]

        if expected_type is None:
            errors.append(f"{path}{field}: tipo '{props['type']}' não suportado no validador")
        elif not isinstance(actual_value, expected_type):
            errors.append(
                f"{path}{field}: esperado {props['type']}, recebido {type(actual_value).__name__}"
            )

        # Validação recursiva para objetos
        if props["type"] == "object":
            nested_schema = props  # já contém 'properties' e possivelmente 'required'
            nested_errors = validate_json(actual_value, nested_schema, path=f"{path}{field}.")
            errors.extend(nested_errors)

    return errors


# --------------------------------------------------------------------
# Rota que o Asaas chamará
# --------------------------------------------------------------------

@app.route("/webhook-asaas", methods=["POST"])
def webhook_handler():
    # 1. Content‑Type deve ser JSON
    if not request.is_json:
        return (
            jsonify(
                {
                    "error": "Content-Type inválido",
                    "message": "O cabeçalho Content-Type deve ser application/json",
                }
            ),
            400,
        )

    # 2. Verifica segredo enviado pelo Asaas
    if request.headers.get("X-Webhook-Secret") != CONFIG["WEBHOOK_SECRET"]:
        return (
            jsonify(
                {
                    "error": "Não autorizado",
                    "message": "Secret do webhook inválido",
                }
            ),
            401,
        )

    # 3. Tenta carregar JSON
    try:
        data = request.get_json(force=True)
    except Exception as exc:
        return (
            jsonify({"error": "JSON inválido", "message": str(exc)}),
            400,
        )

    # 4. Validações básicas (schema)
    validation_errors = validate_json(data, WEBHOOK_SCHEMA)
    if validation_errors:
        return (
            jsonify(
                {
                    "error": "Dados inválidos",
                    "details": validation_errors,
                    "expected_format": WEBHOOK_SCHEMA,
                }
            ),
            400,
        )

    # 5. Processa eventos de pagamento confirmado
    if data["event"] == "PAYMENT_CONFIRMED":
        payment = data["payment"]

        # Regras de negócio adicionais
        if payment["status"] != "CONFIRMED":
            return (
                jsonify(
                    {
                        "error": "Status de pagamento inválido",
                        "message": "Apenas pagamentos CONFIRMED são processados",
                    }
                ),
                400,
            )

        if payment["value"] <= 0:
            return (
                jsonify(
                    {
                        "error": "Valor de pagamento inválido",
                        "message": "O valor do pagamento deve ser positivo",
                    }
                ),
                400,
            )

        try:
            # Busca o cliente no Asaas
            customer_url = f"https://api.asaas.com/v3/customers/{payment['customer']}"
            headers = {"access_token": CONFIG["ASAAS_API_KEY"]}
            response = requests.get(customer_url, headers=headers, timeout=5)

            if response.status_code != 200:
                return (
                    jsonify(
                        {
                            "error": "Falha ao buscar cliente",
                            "details": response.json(),
                        }
                    ),
                    400,
                )

            customer_data = response.json()

            # Simula criação do vendedor (a lógica real dependerá da sua plataforma)
            vendedor = {
                "nome": customer_data.get("name", "Novo Vendedor"),
                "email": customer_data.get("email"),
                "data_criacao": datetime.utcnow().isoformat() + "Z",
                "status": "ativo",
            }

            return jsonify({"status": "success", "vendedor": vendedor}), 200

        except Exception as exc:
            return (
                jsonify(
                    {
                        "error": "Erro ao processar pagamento",
                        "message": str(exc),
                    }
                ),
                500,
            )

    # Qualquer outro evento é ignorado (mas respondemos 200 para o Asaas não re‑enfileirar)
    return jsonify({"status": "ignored"}), 200


# --------------------------------------------------------------------
# Health Check simples
# --------------------------------------------------------------------

@app.route("/")
def health_check():
    return jsonify({"status": "online", "timestamp": datetime.utcnow().isoformat() + "Z"})


# --------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
