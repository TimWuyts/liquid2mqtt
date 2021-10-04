import RPi.GPIO as GPIO
import paho.mqtt.client as mqttc
import configparser
import argparse
import sys
import json
import math
import os
import time

parser = argparse.ArgumentParser(description="Water well level measurement")
parser.add_argument("--config", dest="config", help="Path to config file", default=os.path.dirname(os.path.realpath(__file__)) + os.path.sep + "settings.ini")
parser.add_argument("--verbose", dest="verbose", help="Display feedback")

args = parser.parse_args()

class Liquid2MQTT:
    # reading config & initial setup
    def __init__(self, ini_file):
        # read config
        self.config = configparser.ConfigParser()

        if os.path.isfile(ini_file) == False:
            return print("Config file", ini_file, "not found")

        try:
            self.config.read(ini_file)
        except:
            return print("Config file", ini_file, "found, but cannot be read")

        # check verbose option/argument
        self.verbose = (self.config["DEFAULT"]["VERBOSE"].lower() == "true")

        if len(sys.argv) > 1:
            if args.verbose is not None:
                self.verbose = (args.verbose.lower() == "true")

        # define GPIO pins to use on Raspberry Pi
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(int(self.config["SENSOR"]["GPIO_TRIGGER"]), GPIO.OUT)  # Trigger
        GPIO.setup(int(self.config["SENSOR"]["GPIO_ECHO"]), GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Echo
        GPIO.output(int(self.config["SENSOR"]["GPIO_TRIGGER"]), False)

        self.mqtt_start()
        self.run()

    # run the script, until interrupted using CTRL + C
    def run(self):
        container_length = self.config["CONTAINER"]["LENGTH"]
        container_width = float(self.config["CONTAINER"]["WIDTH"])
        container_height = float(self.config["CONTAINER"]["HEIGHT"])

        # calculating maximum volume in cubic centimeters converted to liters
        if (not container_length):
            # cylindrical container
            max_volume = (math.pow((container_width / 2), 2) * math.pi * container_height) / 1000
        else: 
            # rectangular container
            container_length = float(container_length)
            max_volume = (container_length * container_width * container_height) / 1000

        self.last_status = self.status_object(-1, -1, container_height, -1, max_volume)
        
        try:
            while True:
                raw_distance = self.measure()

                if (raw_distance > -1):
                    # calculating distance
                    distance = raw_distance - float(self.config["SENSOR"]["OFFSET"])
                    level = container_height - distance
                    
                    # calculating volume in cubic centimeters converted to liters
                    if (not container_length):
                        # cylindrical container
                        volume = (math.pow((container_width / 2), 2) * math.pi * level) / 1000
                    else: 
                        # rectangular container
                        volume = (container_length * container_width * level) / 1000

                    if self.verbose: 
                        print("Measured distance = {0:.1f} cm".format(distance))
                        print("Current level = {0:.1f} cm (with maximum level = {1:.1f} cm)".format(level, container_height))
                        print("Current volume = {0:.1f} liters (with maximum volume = {1:.1f} liters)".format(volume, max_volume))
                    
                    self.mqtt_update_status(self.status_object(distance, level, container_height, volume, max_volume))
                else:
                    if self.verbose:
                        print("Measurement failed")

                time.sleep(float(self.config["DEFAULT"]["INTERVAL"]))
        except KeyboardInterrupt:
            print("Measurement stopped")
            GPIO.cleanup()

    # measure the distance from the sensor to the surface
    def measure(self):
        # pulse the trigger/echo line to initiate a measurement
        GPIO.output(int(self.config["SENSOR"]["GPIO_TRIGGER"]), True)
        time.sleep(float(self.config["SENSOR"]["TRIGGER_TIME"]))
        GPIO.output(int(self.config["SENSOR"]["GPIO_TRIGGER"]), False)

        # ensure start time is set in case of very quick return
        start = time.time()
        timeout = start + float(self.config["SENSOR"]["MAX_TIME"])

        # set line to input to check for start of echo response
        while GPIO.input(int(self.config["SENSOR"]["GPIO_ECHO"])) == 0 and start <= timeout:
            start = time.time()

        if (start > timeout):
            return -1

        stop = time.time()
        timeout = stop + float(self.config["SENSOR"]["MAX_TIME"])

        # wait for end of echo response
        while GPIO.input(int(self.config["SENSOR"]["GPIO_ECHO"])) == 1 and stop <= timeout:
            stop = time.time()

        if (stop <= timeout):
            elapsed = stop - start

            # distance = (time elapsed x speed of sound) divided by 2  
            distance = float(elapsed * 34300) / 2.0
        else:
            return -1
        
        return distance

    def status_object(self, distance, level, max_level, volume, max_volume):
        format = "%.1f"

        return { 
            "current_distance": format % distance, 
            "current_level": format % level, 
            "max_level": format % max_level, 
            "current_volume": format % volume, 
            "max_volume": format % max_volume 
        }
    
    def mqtt_start(self):
        def on_connect(client, userdata, flags, rc):
            self.mqtt_update_status(self.last_status)

            if self.verbose:
                print("Connected to MQTT broker at ", self.config["MQTT"]["HOST"])

        self.mqtt = mqttc.Client()
        self.mqtt.on_connect = on_connect

        if len(self.config["MQTT"]["USER"]) > 0 and len(self.config["MQTT"]["PASS"]) > 0:
            self.mqtt.username_pw_set(self.config["MQTT"]["USER"], self.config["MQTT"]["PASS"])
        
        if self.config["MQTT"]["TLS"].lower() == "true":
            if len(self.config["MQTT"]["CERT_PATH"].strip()) > 0:
                self.mqtt.tls_set(self.config["MQTT"]["CERT_PATH"])
            else:
                self.mqtt.tls_set()

        self.mqtt.connect(str(self.config["MQTT"]["HOST"]), int(self.config["MQTT"]["PORT"]), 60)
        self.mqtt.loop_start()
    
    def mqtt_update_status(self, update):
        new_status = dict(self.last_status, **update)

        if json.dumps(new_status) != json.dumps(self.last_status):
            self.last_status = new_status
            self.mqtt.publish(str(self.config["MQTT"]["TOPIC"]), json.dumps(self.last_status), retain = True)

            if self.verbose:
                print("MQTT broker status updated: ", json.dumps(self.last_status))

if __name__ == '__main__':
    liquid2mqtt = Liquid2MQTT(args.config)