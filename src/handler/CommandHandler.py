import sys
import os
import json

from handler.components.start_strategy import StartStrategy


import subprocess
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/data-collector")))
from kraken_data import KrakenOrderBookCollector

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/portfolio-manager")))
from metrics import Metrics

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/execution")))
from execution_trader import SmartTrader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/sub-accounts")))
from logic import SubAccount # Renamed SubAccountWorker to SubAccount for consistency with user provided snippet

class CommandHandler:
    def __init__(self):
        self.metrics = Metrics()
        self.smart_execution = SmartTrader()
        self.sub_account_manager = SubAccount() # Instantiate without args as they are optional

    def start(self, strategy: str, exchange: str, *args, **kwargs):
        """
        METHOD: Start (Strategy) (Exchange) (Args)
        Example: Start sma binance 1h 0.001 0.01
        """
        script_path = os.path.join('src', 'apps', 'strategies', f'{strategy}.py')
    
        if not os.path.isfile(script_path):
            print(f"Strategy script not found: {script_path}")
            #print(f"Current Path: {os.getcwd()}")
            return

        cmd = [sys.executable, script_path, exchange] + list(args)
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Strategy execution failed: {e}")

    def restart(self):
        print("Restarting TradeByte...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def handle(self, command: str, *args, **kwargs):
        cmd = command.split() # Splits the command into a list of arguments based on spaces

        ## TODO: Start Trading a Strategy
        if "start" in cmd:
            try:
                if len(cmd) == 2:
                    self.start(cmd[1], "default", *cmd[2:])
                else:
                    self.start(cmd[1], cmd[2], *cmd[3:])
            except IndexError:
                print('Error handling arguments.')
                print('Example: start sma kraken')
                print('OR')
                print('Example: start sma')
                print('OR')
                print('Example: start sma kraken 5 day 2')
                print('OR')
                print('Example: start sma 5 day 2')
                print('')
            except Exception as e:
                print(f'!!!COMMAND ERROR!!! {e}')
        elif "exit" in cmd or "quit" in cmd:
            sys.exit()
        elif "help" in cmd:
            try:
                with open('src/handler/docs/help.txt', 'r') as f:
                    help_text = f.readlines()
                
                print('')
                for line in help_text:
                    print(line.strip())

            except FileNotFoundError:
                print('Error. help.txt is missing.')
            except Exception as e:
                print(f'!!!COMMAND ERROR!!! {e}')
        elif "path" in cmd:
            print(sys.path)

        elif "portfolio_value" in cmd:
            ##
            ##
            ##
            self.metrics.print_portfolio_summary()

        elif "spread" in cmd:
            pair = cmd[1]
            spread = self.smart_execution.get_spread(pair)
            try:
                print(f'Spread for {pair}: {spread:.2f} basis points')
            except Exception as e:
                print(f'!!! ERROR !!! SmartTrader.get_spread(): {e}')
        
        elif "ask" in cmd or "bid" in cmd:
            pair = cmd[1]
            if cmd[0] == "ask":
                ask = self.smart_execution.get_ask(pair)
                try:
                    print(f'Ask for {pair}: {ask:.2f}')
                except Exception as e:
                    print(f'!!! ERROR !!! SmartTrader.get_ask(): {e}')
            elif cmd[0] == "bid":
                bid = self.smart_execution.get_bid(pair)
                try:
                    print(f'Bid for {pair}: {bid:.2f}')
                except Exception as e:
                    print(f'!!! ERROR !!! SmartTrader.get_bid(): {e}')
        
        elif "price" in cmd:
            pair = cmd[1]
            price = self.smart_execution.get_price(pair)
            try:
                print(f'Price for {pair}: ${price:.2f}')
            except Exception as e:
                print(f'!!! ERROR !!! SmartTrader.get_price(): {e}')

        elif "buy" in cmd or "sell" in cmd:
            ##
            ## struct: smart (side) (pair) (quantity) (threshold -> optional)
            ##
            if cmd[0] == "smart":
                side = cmd[1]
                pair = cmd[2]
                qnty = float(cmd[3])
                try:
                    threshold = float(cmd[4])
                except IndexError:
                    threshold = 10.00
                self.smart_execution._execute_smart_market_order(side,pair,qnty,threshold)

        elif "restart" in cmd:
            self.restart()

        elif "save" in cmd:
            config_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.yaml"))
            bucket_name = "tradebyte-kraken-data"

            collector = KrakenOrderBookCollector(
                config_path=config_path,
                bucket_name=bucket_name
            )
            collector.collect_continuous()
        
        elif "create_account" in cmd:
            if len(cmd) < 5:
                print("Usage: create_account <sub_account_id> <nickname> <created_date> <active_bool>")
                return
            try:
                sub_account_id = int(cmd[1])
                nickname = cmd[2]
                created_date = cmd[3]
                active = cmd[4].lower() == 'true'
                
                new_account_data = {
                    "sub-account": sub_account_id,
                    "nickname": nickname,
                    "balances": {},
                    "created_date": created_date,
                    "active": active
                }
                if self.sub_account_manager.create_account(new_account_data):
                    print(f"Sub-account {nickname} created successfully.")
                else:
                    print(f"Failed to create sub-account {nickname}.")
            except (ValueError, json.JSONDecodeError) as e:
                print(f"Error parsing arguments for create_account: {e}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

        elif "delete_account" in cmd:
            if len(cmd) < 2:
                print("Usage: delete_account <sub_account_id>")
                return
            try:
                sub_account_id = int(cmd[1])
                if self.sub_account_manager.delete_account(sub_account_id):
                    print(f"Sub-account {sub_account_id} deleted successfully.")
                else:
                    print(f"Failed to delete sub-account {sub_account_id}. Not found.")
            except ValueError:
                print("Error: Sub-account ID must be an integer.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

        elif "edit_account" in cmd:
            if len(cmd) < 3:
                print("Usage: edit_account <sub_account_id> <key1>=<value1> <key2>=<value2> ...")
                return
            try:
                sub_account_id = int(cmd[1])
                updated_data = {}
                for arg in cmd[2:]:
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        # Basic type conversion, can be expanded for more complex types
                        if value.lower() == 'true':
                            updated_data[key] = True
                        elif value.lower() == 'false':
                            updated_data[key] = False
                        elif value.isdigit():
                            updated_data[key] = int(value)
                        elif '.' in value and value.replace('.', '', 1).isdigit():
                            updated_data[key] = float(value)
                        else:
                            updated_data[key] = value
                    else:
                        print(f"Warning: Skipping malformed argument '{arg}'. Expected key=value format.")
                
                if self.sub_account_manager.edit_account(sub_account_id, updated_data):
                    print(f"Sub-account {sub_account_id} updated successfully.")
                else:
                    print(f"Failed to edit sub-account {sub_account_id}. Not found.")
            except ValueError:
                print("Error: Sub-account ID must be an integer.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

        elif "transfer_assets" in cmd:
            if len(cmd) < 5:
                print("Usage: transfer_assets <from_sub_account_id> <to_sub_account_id> <currency> <amount>")
                return
            try:
                from_sub_account_id = int(cmd[1])
                to_sub_account_id = int(cmd[2])
                currency = cmd[3]
                amount = float(cmd[4])
                
                if self.sub_account_manager.transfer_assets(from_sub_account_id, to_sub_account_id, currency, amount):
                    print(f"Asset transfer initiated successfully.")
                else:
                    print(f"Asset transfer failed.")
            except ValueError:
                print("Error: Sub-account IDs and amount must be valid numbers.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

        else:
            print(f'Invalid command: {cmd}')
            
