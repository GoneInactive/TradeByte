from rust_kraken_client import rust_kraken_client as kraken
import json
import pandas as pd

"""
This client is used to interact with the rust kraken API.
rust_client -> rust_kraken_client -> kraken_python_client
For lowest latency, use rust_kraken_client directly
"""
class KrakenPythonClient:
    def __init__(self,asset='XBTUSD'):
        self.asset = asset

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
            print(f"KrakenPythonClient.get_bid: {e}")
            return False
    
    def get_ask(self,asset='XBTUSD',index=0):
        """
        Get the ask price of an asset.
        """
        try:
            return kraken.get_ask(asset)[index]
        except TypeError:
            return kraken.get_ask(asset)
        except Exception as e:
            print(f"KrakenPythonClient.get_ask: {e}")
            return False
    
    def get_balance(self,asset=None):
        """
        Get the balance of an asset.
        If asset is None, returns all balances.
        """
        try:
            if asset == None:
                # Returns all balances
                return kraken.get_balance()
            else:
                # Returns specific balance
                return kraken.get_balance()[asset]
        except Exception as e:
            print(f"KrakenPythonClient.get_balance: {e}")
            return False

    def get_spread(self,asset='XBTUSD'):
        """
        Get the spread of an asset.
        """
        try:
            return kraken.get_spread(asset)
        except Exception as e:
            print(f"KrakenPythonClient.get_spread: {e}")
            return False
    
    def add_order(self, asset, side, price, volume):
        """
        Add an order to the Kraken API and return a dictionary with parsed fields.
        """
        try:
            order_response = kraken.add_order(asset, side, price, volume)
            return {
                "txid": order_response.txid[0] if isinstance(order_response.txid, list) else order_response.txid,
                "description": order_response.description
            }
        except Exception as e:
            print(f"KrakenPythonClient.add_order: {e}")
            return False

    
    def get_open_orders(self, asset=None, order_type='open', headers=None):
        """
        Retrieve open orders with optional asset filtering and column selection.
        
        Args:
            asset (str, optional): Filter orders by asset pair (e.g., 'XBTUSD'). Defaults to None.
            order_type (str): Type of orders to retrieve ('open'|'closed'|'both'). Defaults to 'open'.
            headers (list|str, optional): Columns to return. Use '*' for all columns. Defaults to None for basic columns.
        
        Returns:
            pd.DataFrame: DataFrame containing the requested orders
        """
        try:
            # Get and parse orders
            orders_response = kraken.get_open_orders_raw()
            orders_data = json.loads(orders_response)
            orders_dict = orders_data.get('result', {}).get(order_type, {})
            
            if not orders_dict:
                no_orders = pd.DataFrame([{
                    'order_id': None,
                    'descr_pair': asset,
                    'descr_type': 'buy',
                    'descr_price': 0.0,
                    'vol': 0.0,
                    'vol_exec': 0.0
                }])
                return no_orders

            # Convert to DataFrame
            df = (
                pd.DataFrame.from_dict(orders_dict, orient='index')
                .reset_index()
                .rename(columns={'index': 'order_id'})
            )

            # Expand description fields
            if 'descr' in df.columns:
                descr_df = pd.json_normalize(df['descr'])
                descr_df.columns = [f"descr_{col}" for col in descr_df.columns]
                df = pd.concat([df.drop('descr', axis=1), descr_df], axis=1)

            # Filter by asset if specified
            if asset is not None and 'descr_pair' in df.columns:
                df = df[df['descr_pair'] == asset.upper()]

            # Convert data types
            numeric_cols = ['vol', 'vol_exec', 'cost', 'fee', 'price', 'stopprice', 'limitprice']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            time_cols = ['opentm', 'starttm', 'expiretm']
            for col in time_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], unit='s', errors='coerce')

            # Select columns to return
            if headers is None:
                return df[['order_id', 'descr_pair', 'descr_type', 'descr_price', 'vol', 'vol_exec']]
            elif headers == '*' or headers == []:
                return df
            else:
                # Validate requested headers exist
                valid_headers = [h for h in headers if h in df.columns]
                return df[valid_headers]
        except Exception as e:
            print(f"KrakenPythonClient.get_open_orders: {e}")
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
            print(f"KrakenPythonClient.cancel_order: {e}")
            return False
    
    def get_orderbook(self,pair):
        try:
            return kraken.get_orderbook(pair)
        except Exception as e:
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
            print(f"KrakenPythonClient.edit_order: {e}")
            return False
        