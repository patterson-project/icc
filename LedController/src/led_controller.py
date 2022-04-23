import json
from kasa import SmartBulb
from paho.mqtt.client import Client
from rpi_ws281x import Adafruit_NeoPixel
from multiprocessing import Process
from utils import LedRequest, LedConfig, log
from sequences import LedStripSequence
import colorsys


class LedController:
    def __init__(self):
        self.strip: Adafruit_NeoPixel = self.led_strip_init()
        self.client: Client = self.mqtt_init()
        self.sequence: LedStripSequence = LedStripSequence()
        self.led_process: Process = None
        self.request: LedRequest = None
        self.operation_callback_by_name = {
            "off": self.off,
            "hsv": self.hsv,
            "brightness": self.brightness,
            "rainbow": self.rainbow,
            "color_wipe": self.color_wipe,
            "theater_chase": self.theater_chase,
            "rainbow_cycle": self.rainbow_cycle,
            "theater_chase_rainbow": self.theater_chase_rainbow,
        }

    def led_strip_init(self) -> Adafruit_NeoPixel:
        strip = Adafruit_NeoPixel(
            LedConfig.COUNT,
            LedConfig.PIN,
            LedConfig.FREQ_HZ,
            LedConfig.DMA,
            LedConfig.INVERT,
            LedConfig.BRIGHTNESS,
            LedConfig.CHANNEL,
        )
        strip.begin()
        return strip

    def mqtt_init(self) -> Client:
        client = Client("led-controller", clean_session=False)
        client.connect(LedConfig.BROKER_ADDRESS)
        client.on_message = self.on_message
        client.subscribe("home/lighting")
        return client

    def terminate_process(self) -> None:
        if self.led_process is not None:
            self.led_process.terminate()
            self.led_process.join()
            self.led_process = None

    def on_message(self, client, userdata, message) -> None:
        led_request = LedRequest(**json.loads(message.payload))
        log(message.topic, str(led_request.__dict__))

        self.request = led_request
        self.operation_callback_by_name[led_request.operation]()

    def brightness(self):
        if self.led_process is not None:
            last_sequence = self.led_process.name
            self.terminate_process()
            self.strip.setBrightness(int(255 * (int(self.request.brightness) / 100)))
            self.strip.show()
            self.operation_callback_by_name[last_sequence]()
        else:
            self.strip.setBrightness(int(255 * (int(self.request.brightness) / 100)))
            self.strip.show()

    def off(self):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColorRGB(i, 0, 0, 0)
        self.strip.show()

    def hsv(self):
        self.terminate_process()

        r, g, b = tuple(
            round(i * 255)
            for i in colorsys.hsv_to_rgb(
                self.request.h / 360, self.request.s / 100, self.request.v / 100
            )
        )

        for i in range(self.strip.numPixels()):
            self.strip.setPixelColorRGB(i, r, b, g)

        self.strip.show()

    def rainbow(self) -> None:
        self.terminate_process()
        self.led_process = Process(
            target=self.sequence.rainbow, args=(self.strip, self.request.wait_ms)
        )
        self.led_process.name = self.request.operation
        self.led_process.start()

    def rainbow_cycle(self):
        self.terminate_process()
        self.led_process = Process(
            target=self.sequence.rainbow_cycle, args=(self.strip)
        )
        self.led_process.name = self.request.operation
        self.led_process.start()

    def color_wipe(self):
        pass

    def sunrise(self):
        pass

    def theater_chase(self):
        pass

    def theater_chase_rainbow(self):
        pass


if __name__ == "__main__":
    mqtt_client = LedController()
    print("Initialization completed successfully.")

    try:
        mqtt_client.client.loop_forever()
    except SystemError as e:
        mqtt_client.client.loop_stop()
