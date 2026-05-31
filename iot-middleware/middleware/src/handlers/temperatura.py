import logging

from handlers.verificador_handler import validar_valor, criar_resposta

LOGGER = logging.getLogger(__name__)

def processar_temperatura(payload, correlation_id):
    valor = payload.get("valor")

    validar_valor(valor)

    status = "normal"

    if valor > 40:
        status = "critico"

    resultado = criar_resposta(
        sensor = "temperatura",
        valor = valor,
        status = status,
        correlation_id = correlation_id,
    )

    LOGGER.info(
        {
            "evento": "temperatura_processada",
            "resultado": resultado,
        }
    )

    return resultado
