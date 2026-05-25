import logging

from handlers.verificador_handler import validar_valor, criar_resposta

LOGGER = logging.getLogger(__name__)

def processar_pressao(payload, correlation_id):
    valor = payload.get("valor")

    validar_valor(valor)

    status = "normal"

    if valor > 1200:
        status = "alta"

    elif valor < 900:
        status = "baixa"

    resultado = criar_resposta(
        sensor = "pressao",
        valor = valor,
        status = status,
        correlation_id = correlation_id,
    )

    LOGGER.info(
        {
            "evento": "pressao_processada",
            "resultado": resultado,
        }
    )

    return resultado
