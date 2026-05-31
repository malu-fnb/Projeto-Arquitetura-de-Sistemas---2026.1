import logging

LOGGER = logging.getLogger(__name__)

def validar_valor(valor):
    if valor is None:
        raise ValueError("Valor ausente.")

    if not isinstance(valor, (int, float)):
        raise ValueError("Valor deve ser numerico.")


def criar_resposta(sensor, valor, status, correlation_id):
    return {
        "sensor": sensor,
        "valor": valor,
        "status": status,
        "correlation_id": correlation_id,
    }
