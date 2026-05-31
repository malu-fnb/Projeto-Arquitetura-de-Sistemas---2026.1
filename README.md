# Projeto: Middleware Distribuído para IoT - 2° GQ 


O objetivo do projeto é implementar, **do zero** (sem o uso de API Gateways prontos), uma camada de middleware distribuído capaz de gerenciar a comunicação, resiliência, observabilidade e segurança entre serviços de uma aplicação voltada para o domínio de **Monitoramento e IoT**.

---

## Domínio Escolhido & Fluxo da Aplicação

O sistema foi modelado para processar dados de telemetria enviados por sensores distribuídos (dispositivos IoT simulados). 

1. **Dispositivos IoT (Sensores):** Enviam leituras brutas via protocolo MQTT.
2. **Broker MQTT (Eclipse Mosquitto):** Atua como o canal de mensageria assíncrona, exigindo credenciais seguras.
3. **Serviço de Middleware (Python):** Consome os tópicos do broker, injeta metadados arquiteturais e passa as informações brutas pelo módulo de processamento (`parser.py`).
4. **Mapeamento de Serviços:** O ecossistema foi desacoplado de forma que o consumo, o processamento de dados brutas e as operações finais rodem de maneira independente e em containers separados.

---

## Tecnologias Utilizadas

* **Linguagem Principal:** Python 3 (com bibliotecas nativas e drivers de rede)
* **Mensageria/Fila:** Eclipse Mosquitto (Broker MQTT)
* **Ambiente e Orquestração:** Docker & Docker Descktop
