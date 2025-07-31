from rust_kraken_client import rust_kraken_client as kraken
import json
import pandas as pd
import requests
import time

"""
This client is used to interact with the rust kraken API.
rust_client -> rust_kraken_client -> kraken_python_client
For lowest latency, use rust_kraken_client directly
"""
class KrakenPythonClient:
    def __init__(self, asset='XBTUSD', error_message=False, api_key=None, api_secret=None):
        self.asset = asset
        self.error_message = error_message
        self.base_url = "https://api.kraken.com/0/public"
        self.api_key = api_key
        self.api_secret = api_secret

    def test_connection(self):
        try:
            kraken.get_bid('XBTUSD')[0]
            return True
        except:
            return False

    def get_bid(self,asset='XBTUSD',index=0):
        """
        Get the bid price of an asset.
        """
        try:
            return kraken.get_bid(asset)[index]
        except TypeError:
            return kraken.get_bid(asset)
        except Exception as e:
            if self.error_message:
                print(f"KrakenPythonClient.get_bid: {e}")
            return False
        
    def get_ask(self,asset='XBTUSD',index=0):
        """
        Get the bid price of an asset.
        """
        try:
            return kraken.get_ask(asset)[index]
        except TypeError:
            return kraken.get_ask(asset)
        except Exception as e:
            if self.error_message:
                print(f"KrakenPythonClient.get_bid: {e}")
            return False

    def get_order_id(self):
        pass

    def cancel_order(self,order_id):
        """
        Cancel an order from the Kraken API.
        """
        try:
            return kraken.cancel_order(order_id)
        except Exception as e:
            if self.error_message:
                print(f"KrakenPythonClient.cancel_order: {e}")
            return False
    
    def get_orderbook(self,pair):
        try:
            return kraken.get_orderbook(pair)
        except Exception as e:
            if self.error_message:
                print(f"KrakenPythonClient.get_orderbook: {e}")
            return False

    def edit_order(self, txid, pair, side, price, volume, new_userref=None):
        """
        Edit an existing order on the Kraken API.
        
        Args:
            txid (str): The transaction ID of the order to edit
            pair (str): The trading pair (e.g., 'XBTUSD')
            side (str): The order side ('buy' or 'sell')
            price (float): The new price for the order
            volume (float): The new volume for the order
            new_userref (str, optional): New user reference ID for the order
            
        Returns:
            dict: Order response containing txid and description if successful
            bool: False if the operation fails
        """
        try:
            order_response = kraken.edit_order(txid, pair, side, price, volume, new_userref)
            return order_response
        except Exception as e:
            if self.error_message:
                print(f"KrakenPythonClient.edit_order: {e}")
            return False

    def get_my_recent_orders(self, pair=None, since=None, count=None, userref=None):
        """
        Get recent orders for the authenticated user.
        
        Args:
            pair (str, optional): Trading pair to filter orders (e.g., 'XBTUSD'). If None, returns all pairs.
            since (str, optional): Return orders since this order ID
            count (int, optional): Maximum number of orders to return
            userref (str, optional): User reference ID to filter orders
            
        Returns:
            pd.DataFrame: DataFrame containing order history with columns:
                - order_id: Order ID (txid)
                - pair: Trading pair
                - side: 'buy' or 'sell'
                - type: Order type (market, limit, etc.)
                - price: Order price
                - volume: Order volume
                - time: Order timestamp (datetime)
                - status: Order status
                - cost: Order cost
                - fee: Order fee
                - misc: Miscellaneous info
            bool: False if the operation fails
        """
        try:
            # Get orders from the rust client
            orders_response = kraken.get_open_orders(pair, since, count, userref)
            
            # Parse the response if it's JSON string
            if isinstance(orders_response, str):
                orders_data = json.loads(orders_response)
            else:
                orders_data = orders_response
            
            # Extract orders from the result
            if hasattr(orders_data, 'result'):
                result = orders_data.result
            elif isinstance(orders_data, dict) and 'result' in orders_data:
                result = orders_data['result']
            else:
                result = orders_data
            
            # Get the orders dictionary
            if hasattr(result, 'open'):
                orders_dict = result.open
            elif isinstance(result, dict) and 'open' in result:
                orders_dict = result['open']
            else:
                # Assume the result itself is the orders dictionary
                orders_dict = result
            
            if not orders_dict:
                # Return empty DataFrame with expected columns
                return pd.DataFrame(columns=[
                    'order_id', 'pair', 'side', 'type', 'price', 'volume', 'time', 
                    'status', 'cost', 'fee', 'misc'
                ])
            
            # Convert to DataFrame
            df = pd.DataFrame.from_dict(orders_dict, orient='index').reset_index()
            df = df.rename(columns={'index': 'order_id'})
            
            # Extract nested order description if it exists
            if 'descr' in df.columns:
                descr_df = pd.json_normalize(df['descr'])
                df = pd.concat([df.drop('descr', axis=1), descr_df], axis=1)
            
            # Standardize column names and data types
            if 'type' in df.columns and 'side' not in df.columns:
                df['side'] = df['type']
            
            # Convert numeric columns
            numeric_cols = ['price', 'vol', 'cost', 'fee']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Rename volume column if it exists
            if 'vol' in df.columns:
                df['volume'] = df['vol']
            
            # Convert time to datetime
            if 'opentm' in df.columns:
                df['time'] = pd.to_datetime(df['opentm'], unit='s', errors='coerce')
            elif 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'], unit='s', errors='coerce')
            
            # Add status column
            if 'status' not in df.columns:
                df['status'] = 'open'
            
            # Filter by pair if specified
            if pair is not None and 'pair' in df.columns:
                df = df[df['pair'] == pair.upper()]
            
            # Select and order columns to match expected format
            expected_cols = ['order_id', 'pair', 'side', 'type', 'price', 'volume', 'time', 'status', 'cost', 'fee', 'misc']
            available_cols = [col for col in expected_cols if col in df.columns]
            
            # Add missing columns with default values
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = None
            
            return df[expected_cols]
            
        except Exception as e:
            if self.error_message:
                print(f"KrakenPythonClient.get_my_recent_orders: {e}")
            return False
        
    def get_my_recent_trades(self, pair=None, since=None, count=None):
        """
        Get recent trades history for the authenticated user using Kraken REST API.
        
        Args:
            pair (str, optional): Trading pair to filter trades (e.g., 'XBTUSD'). If None, returns all pairs.
            since (str, optional): Return trades since this trade ID
            count (int, optional): Maximum number of trades to return
            
        Returns:
            pd.DataFrame: DataFrame containing trade history with columns:
                - trade_id: Trade ID
                - pair: Trading pair
                - side: 'buy' or 'sell'
                - price: Trade price
                - volume: Trade volume
                - time: Trade timestamp (datetime)
                - cost: Trade cost
                - fee: Trade fee
                - margin: Margin (if applicable)
                - misc: Miscellaneous info
            bool: False if the operation fails
        """
        try:
            # This requires API credentials - you'll need to add them to your class
            if not hasattr(self, 'api_key') or not hasattr(self, 'api_secret'):
                if self.error_message:
                    print("KrakenPythonClient.get_my_recent_trades: API credentials required")
                return False
            
            import urllib.parse
            import hashlib
            import hmac
            import base64
            
            # Kraken private API endpoint
            url = "https://api.kraken.com/0/private/TradesHistory"
            
            # Build parameters
            data = {
                'nonce': str(int(time.time() * 1000))
            }
            
            if pair:
                data['pair'] = pair
            if since:
                data['start'] = since
            if count:
                data['count'] = count
            
            # Create signature for authentication
            postdata = urllib.parse.urlencode(data)
            encoded = (str(data['nonce']) + postdata).encode()
            message = '/0/private/TradesHistory'.encode() + hashlib.sha256(encoded).digest()
            
            mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
            sigdigest = base64.b64encode(mac.digest())
            
            headers = {
                'API-Key': self.api_key,
                'API-Sign': sigdigest.decode()
            }
            
            # Make the request
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            trades_data = response.json()
            
            if trades_data.get('error'):
                if self.error_message:
                    print(f"KrakenPythonClient.get_my_recent_trades: API Error: {trades_data['error']}")
                return False
            
            # Extract trades from the result
            result = trades_data.get('result', {})
            trades_dict = result.get('trades', {})
            
            if not trades_dict:
                # Return empty DataFrame with expected columns
                return pd.DataFrame(columns=[
                    'trade_id', 'pair', 'side', 'price', 'volume', 'time', 
                    'cost', 'fee', 'margin', 'misc'
                ])
            
            # Convert to DataFrame
            df = pd.DataFrame.from_dict(trades_dict, orient='index').reset_index()
            df = df.rename(columns={'index': 'trade_id'})
            
            # Standardize column names and data types
            if 'type' in df.columns:
                df['side'] = df['type']
            
            # Convert numeric columns
            numeric_cols = ['price', 'vol', 'cost', 'fee', 'margin']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Rename volume column if it exists
            if 'vol' in df.columns:
                df['volume'] = df['vol']
            
            # Convert time to datetime
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'], unit='s', errors='coerce')
            
            # Filter by pair if specified (additional filtering after API call)
            if pair is not None and 'pair' in df.columns:
                df = df[df['pair'] == pair.upper()]
            
            # Select and order columns to match expected format
            expected_cols = ['trade_id', 'pair', 'side', 'price', 'volume', 'time', 'cost', 'fee', 'margin', 'misc']
            
            # Add missing columns with default values
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = None
            
            return df[expected_cols]
            
        except Exception as e:
            if self.error_message:
                print(f"KrakenPythonClient.get_my_recent_trades: {e}")
            return False