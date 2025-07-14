import json
import os

class SubAccount:
    def __init__(self, sub_account_id: int, nickname: str, balances: dict, created_date: str, active: bool):
        self.sub_account_id = sub_account_id
        self.nickname = nickname
        self.balances = balances
        self.created_date = created_date
        self.active = active
        self.file_path = os.path.join(os.path.dirname(__file__), 'data', 'sample.json')

    def _read_accounts(self):
        if not os.path.exists(self.file_path):
            return []
        with open(self.file_path, 'r') as f:
            return json.load(f)

    def _write_accounts(self, accounts):
        with open(self.file_path, 'w') as f:
            json.dump(accounts, f, indent=4)

    def create_account(self, new_account_data: dict):
        accounts = self._read_accounts()
        accounts.append(new_account_data)
        self._write_accounts(accounts)
        return True

    def delete_account(self, sub_account_id: int):
        accounts = self._read_accounts()
        initial_len = len(accounts)
        accounts = [account for account in accounts if account['sub-account'] != sub_account_id]
        if len(accounts) < initial_len:
            self._write_accounts(accounts)
            return True
        return False

    def edit_account(self, sub_account_id: int, updated_data: dict):
        accounts = self._read_accounts()
        found = False
        for i, account in enumerate(accounts):
            if account['sub-account'] == sub_account_id:
                accounts[i].update(updated_data)
                found = True
                break
        if found:
            self._write_accounts(accounts)
            return True
        return False
