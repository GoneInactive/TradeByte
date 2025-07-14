import json
import os
import datetime

class SubAccount:
    def __init__(self, sub_account_id: int | None = None, nickname: str | None = None, balances: dict | None = None, created_date: str | None = None, active: bool | None = None):
        self.sub_account_id = sub_account_id
        self.nickname = nickname
        self.balances = balances if balances is not None else {}
        self.created_date = created_date
        self.active = active
        # Define file paths for account data and trade logs
        self.account_data_file = os.path.join(os.path.dirname(__file__), 'data', 'sample.json')
        self.trades_log_file = os.path.join(os.path.dirname(__file__), 'data', 'trades', 'sub_account_trades.json')
        self.transfers_log_file = os.path.join(os.path.dirname(__file__), 'data', 'trades', 'sub_account_transfers.json')

    def _read_json_file(self, file_path):
        if not os.path.exists(file_path):
            return []
        with open(file_path, 'r') as f:
            return json.load(f)

    def _write_json_file(self, data, file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def execute_trade(self, side: str, pair: str, quantity: float, price: float):
        ##
        ## Validate inputs
        ##
        if not all([side, pair, quantity, price]):
            print("Error: All trade parameters (side, pair, quantity, price) must be provided.")
            return False
        if side.lower() not in ['buy', 'sell']:
            print("Error: 'side' must be 'buy' or 'sell'.")
            return False
        if quantity <= 0 or price <= 0:
            print("Error: Quantity and price must be positive values.")
            return False

        ##
        ## Parse pair into base and quote currencies
        ##
        try:
            base_currency, quote_currency = pair.split('/')
        except ValueError:
            print(f"Error: Invalid pair format '{pair}'. Expected format like 'BASE/QUOTE'.")
            return False

        trade_value = quantity * price

        ##
        ## Adjust balances
        ##
        if side.lower() == 'buy':
            if self.balances.get(quote_currency, 0) < trade_value:
                print(f"Error: Insufficient {quote_currency} balance to buy {quantity} of {base_currency}.")
                return False
            self.balances[quote_currency] = self.balances.get(quote_currency, 0) - trade_value
            self.balances[base_currency] = self.balances.get(base_currency, 0) + quantity
        else: # sell
            if self.balances.get(base_currency, 0) < quantity:
                print(f"Error: Insufficient {base_currency} balance to sell {quantity}.")
                return False
            self.balances[base_currency] = self.balances.get(base_currency, 0) - quantity
            self.balances[quote_currency] = self.balances.get(quote_currency, 0) + trade_value

        ##
        ## Log the trade
        ##
        trades = self._read_json_file(self.trades_log_file)
        trade_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "sub_account_id": self.sub_account_id,
            "side": side.lower(),
            "pair": pair,
            "quantity": quantity,
            "price": price,
            "trade_value": trade_value,
            "balances_after_trade": self.balances.copy()
        }
        trades.append(trade_entry)
        self._write_json_file(trades, self.trades_log_file)

        ##
        ## Update the sub-account's data in sample.json (assuming it's a list of accounts)
        ##
        all_accounts = self._read_json_file(self.account_data_file)
        updated_account_found = False
        for i, account in enumerate(all_accounts):
            if account.get('sub-account') == self.sub_account_id:
                all_accounts[i]['balances'] = self.balances
                updated_account_found = True
                break
        if updated_account_found:
            self._write_json_file(all_accounts, self.account_data_file)
        else:
            print(f"Warning: Sub-account with ID {self.sub_account_id} not found in sample.json. Balances not persisted.")

        ##
        ## Print sub-account info after trade
        ##
        print("\nTrade executed successfully! Updated Sub-Account Info:")
        print(f"  Sub-Account ID: {self.sub_account_id}")
        print(f"  Nickname: {self.nickname}")
        print(f"  Balances: {self.balances}")
        print(f"  Active: {self.active}")
        return True
    
    def transfer_assets(self, from_sub_account_id: int, to_sub_account_id: int, currency: str, amount: float):
        # Validate inputs
        if not all([from_sub_account_id, to_sub_account_id, currency, amount]):
            print("Error: All transfer parameters (from_sub_account_id, to_sub_account_id, currency, amount) must be provided.")
            return False
        if from_sub_account_id == to_sub_account_id:
            print("Error: Cannot transfer assets to the same sub-account.")
            return False
        if amount <= 0:
            print("Error: Transfer amount must be positive.")
            return False

        all_accounts = self._read_json_file(self.account_data_file)
        from_account = None
        to_account = None

        for account in all_accounts:
            if account.get('sub-account') == from_sub_account_id:
                from_account = account
            if account.get('sub-account') == to_sub_account_id:
                to_account = account
            if from_account and to_account:
                break

        if not from_account:
            print(f"Error: Source sub-account with ID {from_sub_account_id} not found.")
            return False
        if not to_account:
            print(f"Error: Destination sub-account with ID {to_sub_account_id} not found.")
            return False

        # Check if currency exists and balance is sufficient in source account
        if currency not in from_account.get('balances', {}) or from_account['balances'].get(currency, 0) < amount:
            print(f"Error: Insufficient {currency} balance in source sub-account {from_sub_account_id}.")
            return False

        # Perform the transfer
        from_account['balances'][currency] -= amount
        to_account['balances'][currency] = to_account['balances'].get(currency, 0) + amount

        # Persist updated account data
        self._write_json_file(all_accounts, self.account_data_file)

        # Log the transfer
        transfers = self._read_json_file(self.transfers_log_file)
        transfer_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "from_sub_account_id": from_sub_account_id,
            "to_sub_account_id": to_sub_account_id,
            "currency": currency,
            "amount": amount,
            "from_account_balances_after": from_account['balances'].copy(),
            "to_account_balances_after": to_account['balances'].copy()
        }
        transfers.append(transfer_entry)
        self._write_json_file(transfers, self.transfers_log_file)

        print(f"\nSuccessfully transferred {amount} {currency} from sub-account {from_sub_account_id} to {to_sub_account_id}.")
        print(f"Updated balances for {from_sub_account_id}: {from_account['balances']}")
        print(f"Updated balances for {to_sub_account_id}: {to_account['balances']}")
        return True