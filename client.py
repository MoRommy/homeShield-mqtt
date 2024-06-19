import context
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from gpiozero import PWMLED
from enum import Enum
import base64
import json
import datetime
import threading

MQTT_HOST = "192.168.0.177"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
WHITELIST_PATH = "whitelist.txt"
EVENTS_PATH = "events.txt"
DEVICE_ID = "1001"

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
led = PWMLED(12, active_high=True)


###############################################################################
#                                    EVENTS                                   #
###############################################################################

class Event():
    def __init__(self, action, commander, photo):
        self.action = action
        self.commander = commander
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        self.photo = base64.b64encode(photo).decode('utf-8')

    def to_dict(self):
        return {
            "action": self.action,
            "commander": self.commander,
            "timestamp": self.timestamp,
            "photo": self.photo
        }

    def __str__(self):
        return json.dumps(self.to_dict())

    def log(self):
        with open(EVENTS_PATH, 'a') as file:
            file.write(str(self) + "\n")

def logEvent(action, commander):
    #TODO: Capture & save photo
    print("opennn")
    photo = open("test.jpg", "rb").read()
    event = Event(action, commander, photo)
    print("eveent")
    event.log()

def getEvents():
    events = []
    with open(EVENTS_PATH) as events_file:
        for event in events_file:
            events.append(event)
    return events

#
# MQTT callbacks
#
def on_tc_get_device_history(mosq, obj, msg):
    events = getEvents()
    for event in reversed(events):
        publish.single("TM/" + DEVICE_ID + "/device_history", event, hostname=MQTT_HOST)

#
# Bind callbacks
#
mqttc.message_callback_add(DEVICE_ID + "/get_device_history", on_tc_get_device_history)


###############################################################################
#                                  DOOR STATE                                 #
###############################################################################

class DoorState(Enum):
    CLOSED = 0
    OPEN = 1
    CLOSING = 2
    OPENING = 3

# Initial door state
door_state = DoorState.CLOSED

#
# MQTT callbacks
#
def on_tc_get_device_status(mosq, obj, msg):
    publish.single("TM/" + DEVICE_ID + "/device_status", str(door_state), hostname=MQTT_HOST)

#
# Bind callbacks
#
mqttc.message_callback_add(DEVICE_ID + "/get_device_status", on_tc_get_device_status)


###############################################################################
#                                   OPEN/CLOSE                                #
###############################################################################

#
# Actuator functions
#
def close_door():
    global door_state
    door_state = DoorState.CLOSING
    publish.single("TM/" + DEVICE_ID + "/device_status", str(door_state), hostname=MQTT_HOST)
    led.pulse(fade_in_time = 0, fade_out_time=3, n=1, background=False)
    led.off()
    door_state = DoorState.CLOSED
    publish.single("TM/" + DEVICE_ID + "/device_status", str(door_state), hostname=MQTT_HOST)

def open_door():
    global door_state
    door_state = DoorState.OPENING
    publish.single("TM/" + DEVICE_ID + "/device_status", str(door_state), hostname=MQTT_HOST)
    led.pulse(fade_in_time = 3, fade_out_time=0, n=1, background=False)
    led.on()
    door_state = DoorState.OPEN
    publish.single("TM/" + DEVICE_ID + "/device_status", str(door_state), hostname=MQTT_HOST)

def on_tc_open_thread():
    logEvent("Open", "App User")
    open_door()

def on_tc_close_thread():
    logEvent("Close", "App User")
    close_door()

#
# MQTT callbacks
#
def on_tc_open(mosq, obj, msg):
    threading.Thread(target=on_tc_open_thread).start()
def on_tc_close(mosq, obj, msg):
    threading.Thread(target=on_tc_close_thread).start()


#
# Bind callbacks
#
mqttc.message_callback_add(DEVICE_ID + "/open", on_tc_open)
mqttc.message_callback_add(DEVICE_ID + "/close", on_tc_close)


################################################################################
#                                  WHITELIST                                   #
################################################################################

#
# Whitelist file managers
#
def get_whitelist():
    whitelist = []
    with open(WHITELIST_PATH) as whitelist_file:
        for id in whitelist_file:
            whitelist.append(id.strip())
    return whitelist

def add_to_whitelist(id):
    with open(WHITELIST_PATH, 'a') as whitelist_file:
        whitelist_file.write(id + "\n")

def remove_from_whitelist(id):
    whitelist = get_whitelist()
    whitelist.remove(id)
    with open(WHITELIST_PATH, 'w') as whitelist_file:
        for id in whitelist:
            whitelist_file.write(id + '\n')

#
# MQTT callbacks
#
def on_tc_get_whitelist(mosq, obj, msg):
    print("OK getting WL")
    wl = get_whitelist()
    publish.single("TM/" + DEVICE_ID + "/whitelist", str(wl), hostname=MQTT_HOST)

def on_tc_add_to_whitelist(mosq, obj, msg):
    add_to_whitelist(msg.payload.decode())

def on_tc_remove_from_whitelist(mosq, obj, msg):
    remove_from_whitelist(msg.payload.decode())

#
# Bind callbacks
#
mqttc.message_callback_add(DEVICE_ID + "/get_whitelist", on_tc_get_whitelist)
mqttc.message_callback_add(DEVICE_ID + "/add_to_whitelist", on_tc_add_to_whitelist)
mqttc.message_callback_add(DEVICE_ID + "/remove_from_whitelist", on_tc_remove_from_whitelist)


################################################################################
#                               MQTT CONNECTION                                #
################################################################################
mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
mqttc.subscribe(DEVICE_ID + "/#", 0)
# publish.single("register_device", DEVICE_ID, hostname=MQTT_HOST)
mqttc.loop_forever()
