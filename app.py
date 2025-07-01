@app.route("/webhook-asaas", methods=["POST"])
def webhook_handler():
    try:
        data = request.get_json()
        if not data:
            print("⚠️ Dados do webhook vazios")
            return jsonify({"error": "Dados não fornecidos"}), 400

        print(f"🔔 Webhook recebido: {data}")

        # Verifica se é um evento de pagamento confirmado
        if data.get("event") != "PAYMENT_CONFIRMED":
            print("🟡 Evento ignorado:", data.get("event"))
            return jsonify({"status": "ignored", "event": data.get("event")}), 200

        payment = data.get("payment", {})
        if not payment:
            print("⚠️ Dados de pagamento ausentes")
            return jsonify({"error": "Dados de pagamento ausentes"}), 400

        customer_id = payment.get("customer")
        if not customer_id:
            print("⚠️ Customer ID ausente")
            return jsonify({"error": "Customer ID ausente"}), 400

        # Busca dados do cliente
        customer_data = AsaasAPI.get_customer(customer_id)
        if not customer_data:
            print("⚠️ Cliente não encontrado no Asaas")
            return jsonify({"error": "Cliente não encontrado"}), 404

        email = customer_data.get("email")
        if not email:
            print("⚠️ E-mail do cliente ausente")
            return jsonify({"error": "E-mail do cliente ausente"}), 400

        # Cria o vendedor
        success, response = WebkulAPI.criar_vendedor(email)
        
        if success:
            print(f"✅ Vendedor criado para {email}")
            return jsonify({
                "status": "success",
                "email": email,
                "senha": "12345",
                "webkul_response": response
            }), 200
        else:
            print(f"❌ Falha ao criar vendedor: {response}")
            return jsonify({
                "status": "error",
                "error": "Falha ao criar vendedor no Webkul",
                "details": response
            }), 422

    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        return jsonify({
            "error": "Erro interno do servidor",
            "details": str(e)
        }), 500
