# Liquid2MQTT

## What is it?
A simple Python script that leverages a JSN-SRO4T 2.0 waterproof ultrasonic sensor module, connected to a Raspberry Pi, which broadcasts the results of the measurements using an MQTT broker.

The measurements do need to take place in an enclosed container (cubic or cylindrical) containing a certain liquid. The sensor is mounted at the top of the container and is measuring the distance between the sensor and surface of the liquid at a specified interval. Based upon the measured distance and the container inner dimensions, the volume is also calculated.

## What is needed?
* Raspberry Pi, with GPIO 14 & 15 pins available.
* JSN-SR04T sensor module, version 2.0 supports a voltage range between 3.3 - 5V.
	* TX is connected to GPIO 14 (pin 8).
	* RX is connected to GPIO 15 (pin 10).
	* GND is connected to GND (pin 6).
	* 5V is connected to 3.3V (pin 1).
* Existing & running MQTT broker.

### Good to know...
Connection schema & code is based upon the following StackExchange question/answers:
[https://raspberrypi.stackexchange.com/a/81793](https://raspberrypi.stackexchange.com/a/81793)

## Config
Configuration is managed using `settings.ini` file. Each option is listed below with additional comments explaining the example values.
	
	[DEFAULT]
	VERBOSE = True                  # wether additional output should be visible in the console
	INTERVAL = 5                    # time in seconds between each measurement
	
	[CONTAINER]
	LENGTH =                        # the inner length in centimeters of the container, if not set width is assumed to be the diagonal for a cylindric container
	WIDTH = 236                     # the inner width or diagonal (when length value is not set) in centimeters of the container
	HEIGHT = 228                    # the inner height in centimeters of the container
	
	[SENSOR]
	OFFSET = 40                     # distance in centimeters between sensor and maximum surface level
	GPIO_TRIGGER = 15               # trigger GPIO pin
	GPIO_ECHO = 14                  # echo GPIO pin
	TRIGGER_TIME = 0.00001          # duration time in seconds for sensor trigger
	MAX_TIME = 0.004                # max time in seconds waiting for response
	
	[MQTT]
	HOST = 192.168.0.229            # MQTT broker host
	PORT = 1883                     # MQTT broker port
	USER =                          # MQTT broker username or blank if not needed
	PASS =                          # MQTT broker password or blank if not needed
	TLS = False                     # MQTT broker TLS encryption
	CERT_PATH =                     # MQTT broker path to encryption certificate
	TOPIC = rainwater/status        # MQTT topic to which results are published
	
## Script execution
The script will run until manually interrupted, using the following command.
Additional flags for `--config` and/or `--verbose` option overrides can be passed along.

	python3 liquid2MQTT.py