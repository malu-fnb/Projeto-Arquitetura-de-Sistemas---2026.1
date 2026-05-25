import logging

from handlers.verificador_handler import validar_valor, criar_resposta

LOGGER = logging.getLogger(__name__)

def processar_umidade(payload, correlation_id):
    valor = payload.get("valor")

    validar_valor(valor)

    if valor < 30:
        status = "baixa"

    elif valor > 80:
        status = "alta"

    else:
        status = "normal"

    resultado = criar_resposta(
        sensor = "umidade",
        valor = valor,
        status = status,
        correlation_id = correlation_id,
    )

    LOGGER.info(
        {
            "evento": "umidade_processada",
            "resultado": resultado,
        }
    )

    return resultado
