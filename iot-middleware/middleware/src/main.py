import paho.mqtt.client as mqtt
import time

# Configurações do Broker MQTT (Dentro do Docker, usamos o nome do container)
BROKER = "mosquitto"
PORT = 1883
TOPICO = "sensores/#"

# Função chamada quando o middleware se conecta ao Mosquitto
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[MIDDLEWARE] Conectado com sucesso ao Broker Mosquitto!", flush=True)
        client.subscribe(TOPICO)
        print(f"[MIDDLEWARE] Inscrito no tópico: {TOPICO}", flush=True)
    else:
        print(f"[MIDDLEWARE] Falha na conexão. Código de retorno: {rc}", flush=True)

# Função chamada quando uma nova mensagem de sensor chega
def on_message(client, userdata, msg):
    print(f"[MIDDLEWARE] Mensagem recebida no tópico '{msg.topic}': {msg.payload.decode()}", flush=True)

def main():
    print("[MIDDLEWARE] Inicializando o serviço...", flush=True)
    
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    # Tentativa de conexão com tratamento de erro caso o broker ainda esteja ligando
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            break
        except Exception:
            print("[MIDDLEWARE] Aguardando o Broker Mosquitto iniciar...", flush=True)
            time.sleep(2)

    # Mantém o contêiner vivo ouvindo as mensagens indefinidamente
    client.loop_forever()

if __name__ == "__main__":
    main()