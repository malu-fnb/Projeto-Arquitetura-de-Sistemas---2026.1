def processar_temperatura(payload):
    temperatura = payload.get("valor")

    if temperatura is None:
        raise ValueError("Temperatura ausente")

    status = "normal"

    if temperatura > 40:
        status = "critico"

    return{
        "sensor": "temperatura",
        "valor": temperatura,
        "status": status
    }
