# Projeto: Middleware Distribuído para IoT - 2° GQ 

### Integrantes do Grupo:
* **Antônio Edson Alves de Holanda Neto**
* **Arthur Filipe Leite de Vasconcelos**
* **Dacio da Silva Melo Junior**
* **David Cândido de Souza**
* **Malu de Faria Neves Bezerra**
* **Matheus Fabiano Barbosa Aguiar**

---

## Visão Geral
O objetivo do projeto é implementar, **do zero** (sem o uso de API Gateways prontos), uma camada de middleware distribuído capaz de gerenciar a comunicação, resiliência, observabilidade e segurança entre serviços de uma aplicação voltada para o domínio de **Monitoramento e IoT**.

---

## Domínio Escolhido & Fluxo da Aplicação

O sistema foi modelado para processar dados de telemetria enviados por sensores distribuídos (dispositivos IoT simulados). 

1. **Dispositivos IoT (Sensores):** Enviam leituras brutas utilizando o protocolo leve MQTT.
2. **Broker MQTT (Eclipse Mosquitto):** Atua como o barramento de mensageria assíncrona isolado em container.
3. **Serviço de Middleware (Python):** Consome os tópicos do broker em tempo real, injeta metadados arquiteturais e faz o tratamento defensivo dos pacotes.
4. **Desacoplamento:** O ecossistema foi projetado para garantir que a recepção de dados, a mensageria e o processamento rodem de forma independente e resiliente através de containers interconectados em rede virtual.

---

## Tecnologias Utilizadas

* **Linguagem Principal:** Python 3 (executando em modo *unbuffered* para logs instantâneos)
* **Mensageria/Fila:** Eclipse Mosquitto (Broker MQTT)
* **Ambiente e Orquestração:** Docker & Docker Compose
* **Dependências Python:** Biblioteca `paho-mqtt` para comunicação de rede

---

## Contribuições dos Integrantes


***Antônio Edson Alves de Holanda Neto***

Desafio: Concentrou-se na infraestrutura e controle de versão, lidando com severas dificuldades na configuração de ambiente e na resolução de conflitos complexos de mesclagem de código (merge conflicts) com outras branches concorrentes, afetando diretamente a estabilidade do arquivo principal (main.py).

***Arthur Felipe Leite de Vasconcelos***

Desafio: Responsável pela camada de infraestrutura virtualizada. Enfrentou barreiras no isolamento das redes internas do Docker Compose, na persistência de volumes voláteis para o broker de mensagens e na garantia de que múltiplos containers conseguissem resolver o mapeamento de portas locais de forma transparente.


***Dacio da Silva Melo Junior***

Desafio: Focado no fluxo lógico do ponto de entrada principal (main.py). O principal obstáculo técnico foi desenvolver rotinas de tratamento defensivo de erros para garantir que o script principal não encerrasse sua execução abruptamente na ausência momentânea do broker MQTT, criando loops robustos de reconexão automática.

***David Cândido de Souza***

Desafio: Enfrentou complexidade na curva de aprendizado conceitual sobre sistemas distribuídos orientados a eventos, especificamente na compreensão da macroarquitetura do middleware e em como desacoplar de maneira eficiente o fluxo de comunicação interna entre o cliente MQTT, o módulo de tratamento (parser.py) e os handlers finais.

***Malu de Faria Neves Bezerra***

Desafio: Responsável por diagnosticar e mitigar falhas críticas de runtime no container do middleware. Enfrentou dificuldades na sincronização de caminhos internos do Dockerfile com o script, na resolução do comportamento de silenciamento de logs por conta do buffering padrão do Python em containers (resolvido com o modo unbuffered -u) e na estruturação do gerenciamento de conexões assíncronas persistentes do cliente MQTT.

***Matheus Fabiano Barbosa Aguiar***

Desafio: Responsável pela camada de apresentação de dados e observabilidade em um Dashboard. Teve o desafio de integrar o consumo assíncrono de mensagens MQTT com os gargalos de latência de um dashboard visual em tempo real, mitigando concorrência de concorrência e garantindo que os dados de telemetria fossem renderizados sem perdas, teve dificuldades em fazer a integração entre os dados no dashboard.

---

## Desafios Encontrados

***Antônio Edson Alves de Holanda Neto***

Dificuldade Encontrada:

***Arthur Felipe Leite de Vasconcelos***

Difuculdade Encontrada:

***Dacio da Silva Melo Junior***

Dificuldade Encontrada:

***David Cândido de Souza***

Dificuldade Encontrada:

***Malu de Faria Neves Bezerra***

Dificuldade Encontrada:

***Matheus Fabiano Barbosa Aguiar***

Dificuldade Encontrada:




