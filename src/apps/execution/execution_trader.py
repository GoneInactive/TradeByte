import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "clients")))
from kraken_python_client import KrakenPythonClient


class SmartTrader:
    def __init__(self, asset=None):
        self.exchanges_tradable = []
        self.client = KrakenPythonClient(error_message=True)
        if self.client.test_connection():
            self.exchanges_tradable.append('Kraken')

    def __execute__(self):
        return
    
    def _execute_smart_market_order(self, side: str, pair: str, quantity: float, threshold: float = 10.00) -> bool:
        """
        Executes a "smart" market order.
        Engages various tools to get filled at a better price if spread is >= threshold

        threshold is in basis points
        """
        try:
            ask = self.client.get_ask(pair)
            bid = self.client.get_bid(pair)
            price = ask if side == "sell" else bid
            spread = ((ask/bid)-1)*10000
            if spread <= threshold:
                print('Spread is smaller than threshold. Buying at market')
                print('='*40)
                print(f"{side.upper()} {quantity} {pair.upper()} @ ${price:,.2f}")
                print(f"VALUE: ${quantity*price:,.2f} USD")
                order = self.client.add_order(pair,side,price,quantity)
                print(f'STATUS: {order}')
                print('='*40)
                return order
            
            print('Spread threshold met. Starting smart trader')
            return False

        except Exception as e:
            print(f'!!! ERROR !!! SmartTrader._execute_smart_market_order(): {e}')

    def get_bid_ask(self, pair: str):
        try:
            ask = self.client.get_ask(pair)
            bid = self.client.get_bid(pair)
            return ask, bid
        except Exception as e:
            print(f'!!! ERROR !!! SmartTrader.get_bid_ask(): {e}')
            return None, None
    
    def get_spread(self, pair: str):
        try:
            ask, bid = self.get_bid_ask(pair)
            return ((ask/bid)-1)*10000
        except Exception as e:
            print(f'!!! ERROR !!! SmartTrader.get_spread(): {e}')
            return None
        
    def get_price(self, pair: str):
        try:
            ask, bid = self.get_bid_ask(pair)
            return (ask+bid)/2
        except Exception as e:
            print(f'!!! ERROR !!! SmartTrader.get_price(): {e}')
            return None
        
    def get_ask(self, pair: str):
        try:
            ask, bid = self.get_bid_ask(pair)
            return ask
        except Exception as e:
            print(f'!!! ERROR !!! SmartTrader.get_ask(): {e}')
            return None
        
    def get_bid(self, pair: str):
        try:
            ask, bid = self.get_bid_ask(pair)
            return bid
        except Exception as e:
            print(f'!!! ERROR !!! SmartTrader.get_bid(): {e}')
            return None