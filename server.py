import context
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
from time import sleep

MQTT_HOST = "192.168.0.177"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60

def on_register_device(mosq, obj, msg):
    print("DEVICE REGISTER: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    publish.single("1001", "Welcome to the club!", hostname=MQTT_HOST)

def on_message(mosq, obj, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

mqttc.message_callback_add("register_device/#", on_register_device)
mqttc.on_message = on_message
mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
mqttc.subscribe("#", 0)


mqttc.loop_forever()
