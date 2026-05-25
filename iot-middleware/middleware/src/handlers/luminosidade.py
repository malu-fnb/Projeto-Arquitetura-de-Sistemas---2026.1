def processar_luminosidade(payload):
    valor = payload.get("valor")

    if valor < 100:
        status = "escuro"

    elif valor > 1000:
        status = "muito_claro"

    else:
        status = "normal"

    return{
        "sensor": "luminosidade",
        "valor": valor,
        "status": status
    }
