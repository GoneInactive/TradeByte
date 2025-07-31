
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "clients")))
from kraken_python_client import KrakenPythonClient

client = KrakenPythonClient(
            api_key = "vWofAmTITP1fEEM8TxWaOmeXCIrHi3yfXF5mTzPKTe+OzPiRAQBjrca7", 
            api_secret = "i8Sbg7N8WsnOYVvF61Vdr38eimYE0OKZxuz9x3DOyLQjov9KhCmZGyn1hitgiKIFw2JS01B4OA2x9nS4C+bXKA==")

def main():
    
    print('___1___')
    my_recent_trade_data = client.get_my_recent_trades('EURQ/USD'.replace('/', ''))
    most_recent = my_recent_trade_data.iloc[-1]
    my_recent_trades = {
                "side": most_recent.get('side'), 
                "price": float(most_recent.get('price')), 
                "qty": float(most_recent.get('volume')), 
                "timestamp": most_recent.get('time')
            }
    
    print(my_recent_trades)

    # print('___2___')
    # print(client.get_my_recent_trades('EURQUSD'))
    
if __name__ == "__main__":
    main()