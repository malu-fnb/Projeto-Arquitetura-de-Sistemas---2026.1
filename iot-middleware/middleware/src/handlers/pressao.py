def processar_pressao(payload):
    valor = payload.get("valor")

    status = "normal"

    if valor > 1200:
        status = "alta"

    return {
        "sensor": "pressao",
        "valor": valor,
        "status": status
    }
