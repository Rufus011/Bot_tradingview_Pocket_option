import random
import time

from pocketoptionapi.stable_api import PocketOption

#ssid = (r"""42["auth",{"token":"rzn-lCyF6P","balance":50000}]""")
#ssid = (r""" """)
ssid = (r""" """)
api = PocketOption(ssid,True)

   


def direction():
    # Selecciona aleatoriamente entre 'call' y 'put'
    return random.choice(['call', 'put'])


if __name__ == "__main__":
    api.connect()
    time.sleep(2)

    api.check_connect()
    

    
    ido = (api.buy(1, "AUDNZD_otc", "call", 10))[1]
    #ido = api.check_open()
    print(ido)
    api.check_order_closed(ido)

    ido = (api.buy(1, "AUDNZD_otc", "call", 5))[1]
    #ido = api.check_open()
    print(ido)
    api.check_order_closed(ido)

    while True:
        #if api.check_connect():
           print(api.get_server_timestamp(), "server datetime")
           print(api.get_balance())
           time.sleep(2)

    # Cierra la conexión con la API
