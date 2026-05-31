import logging

from handlers.verificador_handler import validar_valor, criar_resposta

LOGGER = logging.getLogger(__name__)

def processar_luminosidade(payload, correlation_id):
    valor = payload.get("valor")

    validar_valor(valor)

    if valor < 100:
        status = "escuro"

    elif valor > 1000:
        status = "muito_claro"

    else:
        status = "normal"

    resultado = criar_resposta(
        sensor = "luminosidade",
        valor = valor,
        status = status,
        correlation_id = correlation_id,
    )

    LOGGER.info(
        {
            "evento": "luminosidade_processada",
            "resultado": resultado,
        }
    )

    return resultado
