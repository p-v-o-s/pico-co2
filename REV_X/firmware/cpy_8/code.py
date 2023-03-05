'''
Portable CO2 sensor based on RPi pico W running circuitpython 8.0
* SCD-30 CO2 sensor
* Realtime clock
* SD Card
* Wifi connection
* Publish to Adafruit IO (MQTT IoT)
'''

# pylint: disable=no-name-in-module,wrong-import-order
import time
import board
import microcontroller
import busio
import os
import displayio
import terminalio
import wifi
import socketpool
import ssl
import adafruit_ntp
import adafruit_pcf8523
import adafruit_scd30
import adafruit_displayio_ssd1306
from adafruit_display_text import label
from adafruit_display_shapes.sparkline import Sparkline
import adafruit_requests as requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from digitalio import DigitalInOut

displayio.release_displays()

def reset_on_error(delay, error):
    """Resets the code after a specified delay, when encountering an error."""
    print("Error:\n", str(error))
    display.print("Error :(")
    print("Resetting microcontroller in %d seconds" % delay)
    time.sleep(delay)
    microcontroller.reset()

# set up I2C and devices
i2c = busio.I2C(scl=board.GP1, sda=board.GP0,frequency=50000)
scd = adafruit_scd30.SCD30(i2c)
rtc = adafruit_pcf8523.PCF8523(i2c)

# set up display i2c
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64)


## Splash screen

# Make the display context
splash = displayio.Group()
display.show(splash)

color_bitmap = displayio.Bitmap(128, 64, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF  # White

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

# Draw a smaller inner rectangle
inner_bitmap = displayio.Bitmap(118, 48, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0x000000  # Black
inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=5, y=4)
splash.append(inner_sprite)

# Draw a label
text = "PVOS CO2"
text_area = label.Label(terminalio.FONT, text=text, color=0xFFFF00, x=20, y=30, scale = 2)
splash.append(text_area)

time.sleep(1)

# reset the display to show nothing.
display.show(None)

# connect to WIFI
print("Connecting to wifi")
try:
    wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))
# any errors, reset MCU after 10s
except Exception as e:  # pylint: disable=broad-except
    reset_on_error(10, e)
print("Wifi: connected")

# create pool and requests session
pool = socketpool.SocketPool(wifi.radio)
requests = requests.Session(pool, ssl.create_default_context())

# timekeeping
rtc = adafruit_pcf8523.PCF8523(i2c)
ntp = adafruit_ntp.NTP(pool, tz_offset=os.getenv('TZ_OFFSET'))
rtc.datetime = ntp.datetime
t = rtc.datetime
print("Date: %d/%d/%d" % (t.tm_mday, t.tm_mon, t.tm_year))
print("Time: %d:%02d:%02d" % (t.tm_hour, t.tm_min, t.tm_sec))

# Initialize an Adafruit IO HTTP API object
print("Connecting to AdafruitIO")
try:
    io = IO_HTTP(os.getenv('AIO_USERNAME'), os.getenv('AIO_KEY'), requests)
except Exception as e:  # pylint: disable=broad-except
    reset_on_error(10, e)
print("Connected to Adafruit IO")

try:
    # Get the 'co2' feed from Adafruit IO
    co2_feed = io.get_feed("co2-pico")
except AdafruitIO_RequestError:
    # If no 'co2' feed exists, create one
    co2_feed = io.create_new_feed("co2-pico")

try:
    # Get the 'temperature' feed from Adafruit IO
    temp_feed = io.get_feed("temperature-pico")
except AdafruitIO_RequestError:
    # If no 'temperature' feed exists, create one
    temp_feed = io.create_new_feed("temperature-pico")

try:
    # Get the 'humidity' feed from Adafruit IO
    humidity_feed = io.get_feed("humidity-pico")
except AdafruitIO_RequestError:
    # If no 'humidity' feed exists, create one
    humidity_feed = io.create_new_feed("humidity-pico")

## Create background bitmaps and sparklines

# Baseline size of the sparkline chart, in pixels.
chart_width = display.width
chart_height = display.height - 20

# sparkline1 uses a vertical y range between 0 to 10 and will contain a
# maximum of 40 items
sparkline1 = Sparkline(
    width=chart_width,
    height=chart_height,
    #dyn_xpitch=False,
    max_items=100,
    y_min=None, y_max=None, x=0, y=20
)

# Create a group to hold the sparkline and append the sparkline
co2_display = displayio.Group()

# add the sparkline into group
co2_display.append(sparkline1)

# Add co2 value placeholder
co2_text = label.Label(terminalio.FONT, text=" "*20, color=0xFFFF00, x=5, y=5)
co2_display.append(co2_text)

# Add sparkline to the display
display.show(co2_display)


## co2 sensor startup

# scd.temperature_offset = 10
print("Temperature offset:", scd.temperature_offset)

# scd.measurement_interval = 4
print("Measurement interval:", scd.measurement_interval)

# scd.self_calibration_enabled = True
print("Self-calibration enabled:", scd.self_calibration_enabled)

# scd.ambient_pressure = 1100
print("Ambient Pressure:", scd.ambient_pressure)

# scd.altitude = 100
print("Altitude:", scd.altitude, "meters above sea level")

# scd.forced_recalibration_reference = 409
print("Forced recalibration reference:", scd.forced_recalibration_reference)
print("")

###
# Main loop
###
while True:
    try:
        if scd.data_available:
            co2 = scd.CO2
            temp = scd.temperature
            humidity = scd.relative_humidity
            co2_str = "CO2: %d PPM" % (co2)
            temp_str = "Temp: " + str(temp) + " C"
            humidity_str = "Humidity: " + str(humidity) + " %rH"
            print(co2_str)
            print(temp_str)
            print(humidity_str)
            print("Waiting for new data...")
            print("")

            # Create the text label for ssd
            co2_text.text = co2_str
            
            # turn off the auto_refresh of the display while modifying the sparkline
            display.auto_refresh = False

            # add_value: add a new value to a sparkline
            sparkline1.add_value(co2)

            # turn the display auto_refresh back on
            display.auto_refresh = True

            # Send co2 values to the feed
            print("Sending {0} to co2 feed...".format(co2))
            io.send_data(co2_feed["key"], co2)
            io.send_data(temp_feed["key"], temp)
            io.send_data(humidity_feed["key"], humidity)
            print("Data sent!")

        time.sleep(10)
    # any errors, reset MCU
    except Exception as e:  # pylint: disable=broad-except
        reset_on_error(10, e)

