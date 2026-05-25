def processar_umidade(payload):
    valor = payload.get("valor")

    if valor < 30:
        status = "baixa"

    elif valor > 80:
        status = "alta"

    else:
        status = "normal"

    return{
        "sensor": "umidade",
        "valor": valor,
        "status": status
    }
