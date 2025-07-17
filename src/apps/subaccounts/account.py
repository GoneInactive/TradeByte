from typing import Optional
import os
import json
import datetime
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "clients")))
from kraken_python_client import KrakenPythonClient

class AccountEdit:
    def __init__(self, account_id: Optional[int] = -1, nick_name: Optional[str] = None):
        self.account_id = account_id
        self.nick_name = nick_name
        self.data = {
            "account_id": account_id,
            "nick_name": nick_name,
            "balance": {
                "ZUSD": 0.00,
                "ZEUR": 0.00
            }
        }

    def create_account(self):
        ##
        ## Create the accounts directory if it doesn't exist
        ##
        accounts_dir = os.path.join('data', 'accounts')
        os.makedirs(accounts_dir, exist_ok=True)

        ##
        ## Create JSON file with account data
        ##
        filename = f"account_{self.account_id}.json"
        filepath = os.path.join(accounts_dir, filename)
        
        with open(filepath, 'w') as json_file:
            json.dump(self.data, json_file, indent=4)
        
        return filepath
    
    def delete_account(self, account_id: Optional[int] = -1):
        if account_id == -1:
            account_id = self.account_id

        # Construct the file path'src', 'apps', 'sub-accounts', 
        accounts_dir = os.path.join('data', 'accounts')
        filename = f"account_{account_id}.json"
        filepath = os.path.join(accounts_dir, filename)
        
        try:
            # Check if file exists before trying to delete
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            else:
                print(f"Account file not found: {filepath}")
                return False
        except Exception as e:
            print(f"Error deleting account {account_id}: {e}")
            return False

    def edit_account_balance(self, new_balances: dict, account_id: Optional[int] = -1):
        if account_id == -1:
            account_id = self.account_id
        
        # Load current account data to preserve all existing information
        accounts_dir = os.path.join('data', 'accounts')
        filename = f"account_{account_id}.json"
        filepath = os.path.join(accounts_dir, filename)
        
        try:
            # Load existing account data
            if os.path.exists(filepath):
                with open(filepath, 'r') as json_file:
                    current_data = json.load(json_file)
            else:
                print(f"Account file not found: {filepath}")
                return False
            
            # Update only the balances while preserving all other data
            current_data['balances'] = new_balances
            
            # Save the updated data back to the JSON file
            with open(filepath, 'w') as json_file:
                json.dump(current_data, json_file, indent=4)
            return True
        except Exception as e:
            print(f"Error updating account {account_id}: {e}")
            return False

        


class SubAccount:
    def __init__(self, account_id: Optional[int] = None):
        self.account_id = account_id
        self.accounts_dir = os.path.join('data', 'accounts')
        self.client = KrakenPythonClient()

    def _load_account_data(self, account_id: int) -> Optional[dict]:
        """Load account data from JSON file"""
        filename = f"account_{account_id}.json"
        filepath = os.path.join(self.accounts_dir, filename)
        
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as json_file:
                    return json.load(json_file)
            else:
                print(f"Account file not found: {filepath}")
                return None
        except Exception as e:
            print(f"Error loading account {account_id}: {e}")
            return None
    
    def _save_account_data(self, account_id: int, data: dict) -> bool:
        """Save account data to JSON file"""
        filename = f"account_{account_id}.json"
        filepath = os.path.join(self.accounts_dir, filename)
        
        try:
            with open(filepath, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            return True
        except Exception as e:
            print(f"Error saving account {account_id}: {e}")
            return False

    def transfer_funds(self, from_account_id: int, to_account_id: int, asset: str, amount: float) -> bool:
        """
        Transfer funds between two sub-accounts
        
        Args:
            from_account_id: Source account ID
            to_account_id: Destination account ID  
            asset: Currency/asset to transfer (e.g., 'ZUSD', 'ZEUR')
            amount: Amount to transfer
            
        Returns:
            bool: True if transfer successful, False otherwise
        """
        # Load both accounts
        from_account = self._load_account_data(from_account_id)
        to_account = self._load_account_data(to_account_id)
        
        if not from_account or not to_account:
            print("One or both accounts not found")
            return False
        
        # Initialize balances if they don't exist
        if 'balances' not in from_account:
            from_account['balances'] = {}
        if 'balances' not in to_account:
            to_account['balances'] = {}
        
        # Perform the transfer (allowing negative balances)
        from_balance = from_account['balances'].get(asset, 0.0)
        from_account['balances'][asset] = from_balance - amount
        
        to_balance = to_account['balances'].get(asset, 0.0)
        to_account['balances'][asset] = to_balance + amount
        
        # Save both accounts
        if self._save_account_data(from_account_id, from_account) and self._save_account_data(to_account_id, to_account):
            print(f"Successfully transferred {amount} {asset} from account {from_account_id} to account {to_account_id}")
            return True
        else:
            print("Failed to save account data after transfer")
            return False

    def account_value(self, account_id: Optional[int] = None) -> Optional[float]:
        """
        Calculate total account value in USD using real-time prices
        
        Args:
            account_id: Account ID to calculate value for (uses self.account_id if None)
            
        Returns:
            float: Total account value in USD, or None if error
        """
        if account_id is None:
            account_id = self.account_id
            
        if account_id is None:
            print("No account ID provided")
            return None
        
        account_data = self._load_account_data(account_id)
        if not account_data:
            return None
        
        balances = account_data.get('balances', {})
        total_value = 0.0
        
        # USD pairs for common assets
        usd_pairs = {
            'ZUSD': 'ZUSDUSD',  # USD to USD = 1:1
            'ZEUR': 'ZEURUSD',  # EUR to USD
            'XXBT': 'XXBTZUSD', # Bitcoin to USD
            'XETH': 'XETHZUSD', # Ethereum to USD
            'ADA': 'ADAUSD',    # Cardano to USD
            'DOT': 'DOTUSD',    # Polkadot to USD
            'LINK': 'LINKUSD',  # Chainlink to USD
            'LTC': 'LTCUSD',    # Litecoin to USD
            'XRP': 'XRPUSD'     # Ripple to USD
        }
        
        for asset, balance in balances.items():
            try:
                if asset == 'ZUSD':
                    # USD is the base currency, so value = balance
                    total_value += balance
                elif asset in usd_pairs:
                    # Get real-time price for the asset
                    pair = usd_pairs[asset]
                    ask = self.client.get_ask(pair)
                    bid = self.client.get_bid(pair)
                    
                    if ask and bid:
                        # Use mid-point price
                        price = (ask + bid) / 2
                        asset_value = balance * price
                        total_value += asset_value
                        print(f"{asset}: {balance} × ${price:.2f} = ${asset_value:.2f}")
                    else:
                        print(f"Could not get price for {asset}, using 0 value")
                else:
                    # For unknown assets, try to construct a USD pair
                    try:
                        # Try common USD pair formats
                        possible_pairs = [f"{asset}USD", f"{asset}ZUSD", f"X{asset}USD"]
                        price_found = False
                        
                        for pair in possible_pairs:
                            try:
                                ask = self.client.get_ask(pair)
                                bid = self.client.get_bid(pair)
                                if ask and bid:
                                    price = (ask + bid) / 2
                                    asset_value = balance * price
                                    total_value += asset_value
                                    print(f"{asset}: {balance} × ${price:.2f} = ${asset_value:.2f}")
                                    price_found = True
                                    break
                            except:
                                continue
                        
                        if not price_found:
                            print(f"Could not get price for {asset}, using 0 value")
                            
                    except Exception as e:
                        print(f"Error getting price for {asset}: {e}")
                        
            except Exception as e:
                print(f"Error processing {asset}: {e}")
                continue
        
        return total_value

    def post_trade(self, side: str, pair: str, quantity: float, price: float, account_id: Optional[int] = None) -> bool:
        """
        Post a trade to update account balances
        
        Args:
            side: 'BUY' or 'SELL'
            pair: Trading pair (e.g., 'XXBTZUSD')
            quantity: Quantity traded
            price: Price per unit
            account_id: Account ID to update (uses self.account_id if None)
            
        Returns:
            bool: True if trade posted successfully, False otherwise
        """
        if side.upper() != "BUY" and side.upper() != "SELL":
            raise ValueError('!!! ERROR !!! SubAccount.post_trade(): side must be buy or sell')
        
        if account_id is None:
            account_id = self.account_id
            
        if account_id is None:
            print("No account ID provided")
            return False
        
        account_data = self._load_account_data(account_id)
        if not account_data:
            return False
        
        # Parse the trading pair (e.g., 'XXBTZUSD' -> base='XXBT', quote='ZUSD')
        if len(pair) >= 6:
            # Simple parsing - assumes 4-char base currency
            base_currency = pair[:4]
            quote_currency = pair[4:]
            # Remove leading slash if present
            if quote_currency.startswith('/'):
                quote_currency = quote_currency[1:]
            # Normalize quote currency: if it does not start with 'Z', convert to 'Z' + quote_currency
            if not quote_currency.startswith('Z'):
                quote_currency = 'Z' + quote_currency
        else:
            print(f"Invalid trading pair format: {pair}")
            return False
        
        # Initialize balances if they don't exist
        if 'balances' not in account_data:
            account_data['balances'] = {}
        
        balances = account_data['balances']
        total_value = quantity * price
        
        if side.upper() == "BUY":
            # Buying: spend quote currency, receive base currency (allowing negative balances)
            quote_balance = balances.get(quote_currency, 0.0)
            balances[quote_currency] = quote_balance - total_value
            balances[base_currency] = balances.get(base_currency, 0.0) + quantity
            
        else:  # SELL
            # Selling: spend base currency, receive quote currency (allowing negative balances)
            base_balance = balances.get(base_currency, 0.0)
            balances[base_currency] = base_balance - quantity
            balances[quote_currency] = balances.get(quote_currency, 0.0) + total_value
        
        # Update account data and save
        account_data['balances'] = balances
        
        # Create trade record
        ##
        ## Quote currency is '/(CURRENCY)' but needs to 'Z(CURRENCY)'
        ##
        trade_record = {
            'timestamp': str(datetime.datetime.now()),
            'side': side.upper(),
            'pair': pair,
            'quantity': quantity,
            'price': price,
            'total_value': total_value,
            'account_id': account_id,
            'base_currency': base_currency,
            'quote_currency': quote_currency,
            'balances_after': balances.copy()  # Store balances after trade
        }
        
        # Add trade to account history
        if 'trade_history' not in account_data:
            account_data['trade_history'] = []
        account_data['trade_history'].append(trade_record)
        
        # Save account data
        if not self._save_account_data(account_id, account_data):
            print("Failed to save account data after trade")
            return False
        
        # Log trade to separate trades file
        if not self._log_trade_to_file(account_id, trade_record):
            print("Warning: Failed to log trade to trades file")
        
        print(f"Trade posted successfully: {side} {quantity} {pair} at {price}")
        return True
    
    def _log_trade_to_file(self, account_id: int, trade_record: dict) -> bool:
        """
        Log a trade to the account's trades file
        
        Args:
            account_id: Account ID
            trade_record: Trade record to log
            
        Returns:
            bool: True if logged successfully, False otherwise
        """
        try:
            # Create trades directory if it doesn't exist
            trades_dir = os.path.join('data', 'trades')
            os.makedirs(trades_dir, exist_ok=True)
            
            # Define trades file path
            trades_filename = f"{account_id}_trades.json"
            trades_filepath = os.path.join(trades_dir, trades_filename)
            
            # Append the new trade as a JSON line
            with open(trades_filepath, 'a') as f:
                f.write(json.dumps(trade_record) + '\n')
            
            return True
            
        except Exception as e:
            print(f"Error logging trade to file: {e}")
            return False
        
    def get_balance(self, account_id: int, asset: str) -> Optional[float]:
        """
        Get the balance of a specific asset for a given account
        
        Args:
            account_id: Account ID to check
            asset: Asset to get balance for (e.g., 'ZUSD', 'XXBT', 'XETH')
            
        Returns:
            float: Balance of the asset, or None if account/asset not found
        """
        account_data = self._load_account_data(account_id)
        if not account_data:
            print(f"Account {account_id} not found")
            return None
        
        balances = account_data.get('balances', {})
        balance = balances.get(asset, 0.0)
        
        return balance
        

