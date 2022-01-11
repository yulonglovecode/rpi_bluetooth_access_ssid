from get_deviceStatus import deviceStatus
from gi.repository import GLib

# Bluezero modules
from bluezero import adapter
from bluezero import peripheral
from bluezero import device
import json
import time
import subprocess

# constants
UART_SERVICE = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
RX_CHARACTERISTIC = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
TX_CHARACTERISTIC = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'

ble_uart = ""


class UARTDevice:
    tx_obj = None

    @classmethod
    def run_wifi_connect(cls, data):
        global ble_uart

        if data.__contains__('ssid'):
            ssid = data['ssid']
        else:
            print('No ssid parameter!')
            return

        if data.__contains__('password'):
            psk = data['password']
        else:
            psk = ''

        print(f'ssid : {ssid}, password : {psk}')
        # remove peripheral and advertisement
        # ble_uart.unpublish()

        wpa_supplicant_conf = "/etc/wpa_supplicant/wpa_supplicant.conf"
        with open(wpa_supplicant_conf, 'a+') as f:
            config_lines = ['\n',
                            'network={',
                            '\tssid="{}"'.format(ssid),
                            '\tpsk="{}"'.format(psk),
                            '\tkey_mgmt=WPA-PSK', '}']
            config = '\n'.join(config_lines)
            print(config)
            f.write(config)

        subprocess.call(['wpa_cli', '-i', 'wlan0', 'reconfigure'])
        time.sleep(10)
        # # write wifi config to file
        # with open(wpa_supplicant_conf, 'w+') as f:
        #     f.write('network={\n')
        #     f.write('    ssid="' + ssid + '"\n')
        #     f.write('    psk="' + psk + '"\n')
        #     f.write('}\n')

        # Restart wifi adapter
        # subprocess.call(['sudo', 'ifconfig', 'wlan0', 'down'])
        # time.sleep(2)
        #
        # subprocess.call(['sudo', 'ifconfig', 'wlan0', 'up'])
        # time.sleep(6)
        #
        # subprocess.call(['sudo', 'killall', 'wpa_supplicant'])
        # time.sleep(1)
        # subprocess.call(['sudo', 'wpa_supplicant', '-B', '-i', 'wlan0', '-c', wpa_supplicant_conf])
        # time.sleep(2)
        # subprocess.call(['sudo', 'dhcpcd', 'wlan0'])
        # time.sleep(10)

        ble_uart.unpublish()
        print("quit bluetooth")

    @classmethod
    def on_connect(cls, ble_device: device.Device):
        print("Connected to " + str(ble_device.address))

    @classmethod
    def on_disconnect(cls, adapter_address, device_address):
        print("Disconnected from " + device_address)

    @classmethod
    def uart_notify(cls, notifying, characteristic):
        if notifying:
            cls.tx_obj = characteristic
        else:
            cls.tx_obj = None

    @classmethod
    def update_tx(cls, value):
        if cls.tx_obj:
            print("Sending")
            cls.tx_obj.set_value(value)

    @classmethod
    def uart_write(cls, value, options):
        print('raw bytes:', value)
        print('With options:', options)
        print('Text value:', bytes(value).decode('utf-8'))
        # feedback notify to APP
        cls.update_tx(value)

        # json processing
        json_data = json.loads(bytes(value).decode('utf-8'))
        # print(json_data)
        if json_data.__contains__('ssid') and json_data.__contains__('password'):
            cls.run_wifi_connect(json_data)


def main(adapter_address):
    global ble_uart

    last4byte_mac = deviceStatus.getWlan0MAC_last4char()
    localName = 'Gogo Wifi config ' + str(last4byte_mac)

    ble_uart = peripheral.Peripheral(adapter_address, local_name=localName)
    ble_uart.add_service(srv_id=1, uuid=UART_SERVICE, primary=True)
    ble_uart.add_characteristic(srv_id=1, chr_id=1, uuid=RX_CHARACTERISTIC,
                                value=[], notifying=False,
                                flags=['write', 'write-without-response'],
                                write_callback=UARTDevice.uart_write,
                                read_callback=None,
                                notify_callback=None)
    ble_uart.add_characteristic(srv_id=1, chr_id=2, uuid=TX_CHARACTERISTIC,
                                value=[], notifying=False,
                                flags=['notify'],
                                notify_callback=UARTDevice.uart_notify,
                                read_callback=None,
                                write_callback=None)

    ble_uart.on_connect = UARTDevice.on_connect
    ble_uart.on_disconnect = UARTDevice.on_disconnect

    ble_uart.publish()


if __name__ == '__main__':
    main(list(adapter.Adapter.available())[0].address)
