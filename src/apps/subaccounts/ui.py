import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from typing import Optional, Dict, List
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from account import SubAccount, AccountEdit
except:
    try:
        from src.apps.subaccounts.account import SubAccount, AccountEdit
    except Exception as e:
        print(f"C.Error: {e}")
import datetime

class SubAccountUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TradeByte Sub-Account Manager")
        self.root.geometry("1500x950")
        self.root.minsize(1300, 800)
        
        # Initialize components
        self.sub_account_manager = SubAccount()
        self.accounts_dir = os.path.join('data', 'accounts')
        self.prices_file = os.path.join('data', 'cached_prices.json')
        
        # Data storage with persistent caching
        self.accounts_data = {}
        self.selected_account_id = None
        self.price_cache = {}  # Cache for API prices
        
        # Threading for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.loading_in_progress = False
        self.fetching_prices = False
        
        # Load cached prices on startup
        self.load_cached_prices()
        
        # Setup styles
        self.setup_styles()
        
        # Create UI components
        self.create_widgets()
        
        # Load accounts asynchronously
        self.async_load_accounts()
        
    def load_cached_prices(self):
        """Load cached prices from file"""
        try:
            if os.path.exists(self.prices_file):
                with open(self.prices_file, 'r') as f:
                    self.price_cache = json.load(f)
                print(f"Loaded {len(self.price_cache)} cached prices")
            else:
                # Ensure the data directory exists
                os.makedirs(os.path.dirname(self.prices_file), exist_ok=True)
                self.price_cache = {}
                print("No cached prices found, starting with empty cache")
        except Exception as e:
            print(f"Error loading cached prices: {e}")
            self.price_cache = {}
    
    def save_cached_prices(self):
        """Save cached prices to file"""
        try:
            os.makedirs(os.path.dirname(self.prices_file), exist_ok=True)
            with open(self.prices_file, 'w') as f:
                json.dump(self.price_cache, f, indent=2)
            print(f"Saved {len(self.price_cache)} cached prices")
        except Exception as e:
            print(f"Error saving cached prices: {e}")
    
    def refresh_all_prices(self):
        """Refresh all prices by fetching from API"""
        if self.fetching_prices:
            messagebox.showinfo("Info", "Price refresh already in progress")
            return
        
        self.fetching_prices = True
        self.status_label.config(text="Refreshing prices...")
        
        def fetch_prices_task():
            try:
                # Get all unique assets from accounts
                all_assets = set()
                for account_data in self.accounts_data.values():
                    balances = account_data.get('balances', {})
                    all_assets.update(balances.keys())
                
                if not all_assets:
                    return {}
                
                print(f"Fetching prices for {len(all_assets)} assets: {list(all_assets)}")
                
                new_prices = {}
                
                # USD pairs for common assets - using correct Kraken pair names
                pair_mappings = {
                    'ZUSD': ('ZUSDUSD', 1.0),    # USD to USD = 1:1
                    'ZEUR': ('EURUSD', None),    # This might not exist on Kraken, try EURFUSD
                    'XXBT': ('XXBTZUSD', None),  # Bitcoin to USD
                    'XETH': ('XETHZUSD', None),  # Ethereum to USD
                    'ADA': ('ADAUSD', None),     # Cardano to USD
                    'DOT': ('DOTUSD', None),     # Polkadot to USD
                    'LINK': ('LINKUSD', None),   # Chainlink to USD
                    'LTC': ('LTCUSD', None),     # Litecoin to USD
                    'XRP': ('XRPUSD', None)      # Ripple to USD
                }
                
                for asset in all_assets:
                    try:
                        if asset == 'ZUSD':
                            new_prices[asset] = 1.0
                            print(f"Price for {asset}: $1.00 (fixed)")
                        elif asset in pair_mappings:
                            pair, fixed_price = pair_mappings[asset]
                            if fixed_price:
                                new_prices[asset] = fixed_price
                                print(f"Price for {asset}: ${fixed_price} (fixed)")
                            else:
                                # Make API call with error handling
                                try:
                                    ask = self.sub_account_manager.client.get_ask(pair)
                                    bid = self.sub_account_manager.client.get_bid(pair)
                                    
                                    # Validate that we got numeric values
                                    if ask and bid and isinstance(ask, (int, float)) and isinstance(bid, (int, float)):
                                        new_prices[asset] = (float(ask) + float(bid)) / 2
                                        print(f"Price for {asset} ({pair}): ${new_prices[asset]:.2f}")
                                    else:
                                        print(f"Invalid price data for {asset}: ask={ask}, bid={bid}")
                                        # Keep old price if available, otherwise set to 0
                                        new_prices[asset] = self.price_cache.get(asset, 0.0)
                                except Exception as api_error:
                                    print(f"API error for {asset} ({pair}): {api_error}")
                                    # Keep old price if available, otherwise set to 0
                                    new_prices[asset] = self.price_cache.get(asset, 0.0)
                        else:
                            # For unknown assets, try multiple pair formats
                            price_found = False
                            possible_pairs = [
                                f"{asset}USD",      # Standard format
                                f"{asset}ZUSD",     # Kraken Z-prefix format
                                f"X{asset}USD",     # Kraken X-prefix format
                                f"X{asset}ZUSD"     # Combined prefix format
                            ]
                            
                            for test_pair in possible_pairs:
                                try:
                                    ask = self.sub_account_manager.client.get_ask(test_pair)
                                    bid = self.sub_account_manager.client.get_bid(test_pair)
                                    
                                    if ask and bid and isinstance(ask, (int, float)) and isinstance(bid, (int, float)):
                                        new_prices[asset] = (float(ask) + float(bid)) / 2
                                        price_found = True
                                        print(f"Found price for {asset} using pair {test_pair}: ${new_prices[asset]:.2f}")
                                        break
                                except:
                                    continue
                            
                            if not price_found:
                                print(f"Could not find valid price for unknown asset: {asset}")
                                # Keep old price if available, otherwise set to 0
                                new_prices[asset] = self.price_cache.get(asset, 0.0)
                    
                    except Exception as e:
                        print(f"Error processing asset {asset}: {e}")
                        # Keep old price if available, otherwise set to 0
                        new_prices[asset] = self.price_cache.get(asset, 0.0)
                
                return new_prices
                
            except Exception as e:
                print(f"Error in fetch_prices_task: {e}")
                return {}
        
        def on_prices_complete(future):
            try:
                new_prices = future.result()
                # Update UI in main thread
                self.root.after(0, self._update_prices_after_fetch, new_prices)
            except Exception as e:
                print(f"Error completing price fetch: {e}")
                self.root.after(0, lambda: self.status_label.config(text="Error refreshing prices"))
            finally:
                self.fetching_prices = False
        
        future = self.executor.submit(fetch_prices_task)
        future.add_done_callback(on_prices_complete)
    
    def _update_prices_after_fetch(self, new_prices):
        """Update UI after prices are fetched"""
        if new_prices:
            self.price_cache = new_prices
            self.save_cached_prices()
            self.status_label.config(text=f"Refreshed {len(new_prices)} prices")
            
            # Update overview with new prices
            self.async_update_overview()
        else:
            self.status_label.config(text="No prices to refresh")
        
    def setup_styles(self):
        """Configure modern dark theme matching speedy.py"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        accent_color = "#4a9eff"
        
        self.root.configure(bg=bg_color)
        
        # Configure styles
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), 
                       background=bg_color, foreground=fg_color)
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), 
                       background=bg_color, foreground=fg_color)
        style.configure('Status.TLabel', font=('Arial', 10), 
                       background=bg_color, foreground=accent_color)
        style.configure('Stat.TLabel', font=('Arial', 10, 'bold'), 
                       background=bg_color, foreground=fg_color)
        style.configure('StatValue.TLabel', font=('Arial', 12, 'bold'), 
                       background=bg_color, foreground=accent_color)
        style.configure('StatValueSmall.TLabel', font=('Arial', 10), 
                       background=bg_color, foreground=accent_color)
        
        # Configure treeview
        style.configure('Treeview', background="#3c3c3c", 
                       foreground=fg_color, fieldbackground="#3c3c3c")
        style.configure('Treeview.Heading', background="#4a4a4a", 
                       foreground=fg_color, font=('Arial', 10, 'bold'))
        
        # Configure buttons
        style.configure('Action.TButton', font=('Arial', 11, 'bold'))
        style.configure('Primary.TButton', font=('Arial', 11, 'bold'))

    def get_cached_price(self, asset: str) -> float:
        """Get cached price (no API calls)"""
        return self.price_cache.get(asset, 0.0)
    
    def calculate_account_value_fast(self, account_data: dict) -> float:
        """Fast calculation of account value using cached prices only"""
        balances = account_data.get('balances', {})
        if not balances:
            return 0.0
        
        # Filter out zero balances
        non_zero_balances = {asset: balance for asset, balance in balances.items() if balance != 0}
        if not non_zero_balances:
            return 0.0
        
        total_value = 0.0
        for asset, balance in non_zero_balances.items():
            price = self.get_cached_price(asset)
            asset_value = balance * price
            total_value += asset_value
            
            # Debug output for troubleshooting
            if price > 0:
                print(f"Account value calc: {asset} = {balance:.6f} × ${price:.2f} = ${asset_value:.2f}")
            elif balance > 0:
                print(f"Account value calc: {asset} = {balance:.6f} × $0.00 (no price cached)")
        
        return total_value

    def async_load_accounts(self):
        """Load accounts asynchronously to prevent UI blocking"""
        if self.loading_in_progress:
            return
            
        self.loading_in_progress = True
        self.status_label.config(text="Loading accounts...")
        
        def load_task():
            try:
                new_accounts_data = {}
                
                if not os.path.exists(self.accounts_dir):
                    return new_accounts_data
                
                # Load all account files
                account_files = [f for f in os.listdir(self.accounts_dir) if f.endswith('.json')]
                
                for filename in account_files:
                    try:
                        filepath = os.path.join(self.accounts_dir, filename)
                        with open(filepath, 'r') as f:
                            account_data = json.load(f)
                            account_id = account_data.get('account_id')
                            if account_id:
                                new_accounts_data[account_id] = account_data
                    except Exception as e:
                        print(f"Error loading account {filename}: {e}")
                
                return new_accounts_data
                
            except Exception as e:
                print(f"Error in load_task: {e}")
                return {}
        
        def on_complete(future):
            try:
                new_accounts_data = future.result()
                # Update UI in main thread
                self.root.after(0, self._update_ui_after_load, new_accounts_data)
            except Exception as e:
                print(f"Error completing load: {e}")
                self.root.after(0, lambda: self.status_label.config(text="Error loading accounts"))
            finally:
                self.loading_in_progress = False
        
        future = self.executor.submit(load_task)
        future.add_done_callback(on_complete)
    
    def _update_ui_after_load(self, new_accounts_data):
        """Update UI components after accounts are loaded"""
        self.accounts_data = new_accounts_data
        
        # Update account listbox
        self.account_listbox.delete(0, tk.END)
        for account_id, account_data in self.accounts_data.items():
            nickname = account_data.get('nick_name', f'Account {account_id}')
            self.account_listbox.insert(tk.END, f"{account_id}: {nickname}")
        
        # Update combo boxes
        account_list = [f"{id}: {data.get('nick_name', f'Account {id}')}" 
                       for id, data in self.accounts_data.items()]
        self.from_account_combo['values'] = account_list
        self.to_account_combo['values'] = account_list
        self.trade_account_combo['values'] = account_list
        
        # Update asset dropdown
        self.update_asset_dropdown()
        
        # Update overview (using cached prices)
        self.async_update_overview()
        
        cached_count = len(self.price_cache)
        self.status_label.config(text=f"Loaded {len(self.accounts_data)} accounts (using {cached_count} cached prices)")
    
    def load_accounts(self):
        """Public method to reload accounts (also refreshes prices)"""
        # First refresh prices, then load accounts
        self.refresh_all_prices()
        self.async_load_accounts()
        
    def update_asset_dropdown(self):
        """Update the asset dropdown with all available assets from accounts"""
        common_assets = ['ZUSD', 'ZEUR', 'XXBT', 'XETH', 'ADA', 'DOT', 'LINK', 'LTC', 'XRP']
        all_assets = set(common_assets)
        
        # Add all assets from existing accounts
        for account_data in self.accounts_data.values():
            balances = account_data.get('balances', {})
            all_assets.update(balances.keys())
        
        all_assets = sorted(list(all_assets))
        
        # Update the asset combo if it exists
        if hasattr(self, 'asset_combo'):
            self.asset_combo['values'] = all_assets

    def async_update_overview(self):
        """Update overview statistics asynchronously using cached prices"""
        def calculate_stats():
            try:
                total_accounts = len(self.accounts_data)
                active_accounts = sum(1 for data in self.accounts_data.values() if data.get('active', False))
                
                # Calculate portfolio stats using cached prices only
                total_value = 0.0
                account_values = []
                largest_account = None
                largest_value = 0.0
                last_activity = "No activity"
                
                for account_id, account_data in self.accounts_data.items():
                    account_value = self.calculate_account_value_fast(account_data)
                    total_value += account_value
                    account_values.append(account_value)
                    
                    if account_value > largest_value:
                        largest_value = account_value
                        largest_account = account_data.get('nick_name', f'Account {account_id}')
                    
                    # Get last activity
                    trade_history = account_data.get('trade_history', [])
                    if trade_history:
                        last_trade = trade_history[-1]['timestamp']
                        if last_activity == "No activity" or last_trade > last_activity:
                            last_activity = last_trade
                
                avg_account_value = total_value / total_accounts if total_accounts > 0 else 0.0
                
                return {
                    'total_accounts': total_accounts,
                    'active_accounts': active_accounts,
                    'total_value': total_value,
                    'avg_account_value': avg_account_value,
                    'largest_account': largest_account,
                    'last_activity': last_activity,
                    'account_values': account_values
                }
                
            except Exception as e:
                print(f"Error calculating stats: {e}")
                return None
        
        def on_stats_complete(future):
            try:
                stats = future.result()
                if stats:
                    self.root.after(0, self._update_overview_ui, stats)
            except Exception as e:
                print(f"Error in stats calculation: {e}")
        
        future = self.executor.submit(calculate_stats)
        future.add_done_callback(on_stats_complete)
    
    def _update_overview_ui(self, stats):
        """Update overview UI with calculated stats"""
        try:
            # Update statistics labels
            self.total_accounts_label.config(text=f"{stats['total_accounts']}")
            self.total_value_label.config(text=f"${stats['total_value']:,.2f}")
            self.active_accounts_label.config(text=f"{stats['active_accounts']}")
            self.largest_account_label.config(text=f"{stats['largest_account']}" if stats['largest_account'] else "--")
            self.avg_account_value_label.config(text=f"${stats['avg_account_value']:,.2f}")
            self.last_activity_label.config(text=f"{stats['last_activity']}")
            
            # Update summary table
            for item in self.summary_tree.get_children():
                self.summary_tree.delete(item)
            
            for i, (account_id, account_data) in enumerate(self.accounts_data.items()):
                account_value = stats['account_values'][i] if i < len(stats['account_values']) else 0.0
                
                # Get last activity
                trade_history = account_data.get('trade_history', [])
                last_activity = "No activity"
                if trade_history:
                    try:
                        last_activity = trade_history[-1].get('timestamp', 'No activity')
                        # Format timestamp if it's a datetime string
                        if isinstance(last_activity, str) and last_activity != 'No activity':
                            # Try to parse and format the datetime
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                                last_activity = dt.strftime('%Y-%m-%d %H:%M')
                            except:
                                pass  # Keep original string if parsing fails
                    except:
                        last_activity = "No activity"
                
                self.summary_tree.insert('', tk.END, values=(
                    account_id,
                    account_data.get('nick_name', f'Account {account_id}'),
                    'Active' if account_data.get('active', False) else 'Inactive',
                    f"${account_value:,.2f}",
                    last_activity
                ))
                
        except Exception as e:
            print(f"Error updating overview UI: {e}")
            # Set default values if update fails
            self.total_accounts_label.config(text="Error")
            self.total_value_label.config(text="$0.00")
            self.active_accounts_label.config(text="0")

    def create_widgets(self):
        """Create all UI widgets with modern dark theme"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text="TradeByte Sub-Account Manager", 
                               style='Title.TLabel')
        title_label.pack(side="left")
        
        # Connection status
        self.connection_status = ttk.Label(header_frame, text="● Connected", 
                                         style='Status.TLabel')
        self.connection_status.pack(side="right")
        
        # Top panel with controls and stats
        top_panel = ttk.Frame(main_frame)
        top_panel.pack(fill="x", pady=(0, 20))
        
        # Left side - Quick actions
        left_panel = ttk.Frame(top_panel)
        left_panel.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Quick actions frame
        actions_frame = ttk.LabelFrame(left_panel, text="Quick Actions", padding="10")
        actions_frame.pack(fill="x")
        
        # Action buttons
        ttk.Button(actions_frame, text="Create Account", 
                  command=self.create_account_dialog, style='Action.TButton').pack(side="left", padx=(0, 10))
        ttk.Button(actions_frame, text="Delete Account", 
                  command=self.delete_account, style='Action.TButton').pack(side="left", padx=(0, 10))
        ttk.Button(actions_frame, text="Refresh All", 
                  command=self.load_accounts, style='Action.TButton').pack(side="left", padx=(0, 10))
        ttk.Button(actions_frame, text="Refresh Prices", 
                  command=self.refresh_all_prices, style='Action.TButton').pack(side="left")
        
        # Right side - Statistics
        right_panel = ttk.Frame(top_panel)
        right_panel.pack(side="right", fill="y")
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(right_panel, text="Portfolio Statistics", padding="10")
        stats_frame.pack(fill="both", expand=True)
        
        # Create two columns for statistics
        stats_left = ttk.Frame(stats_frame)
        stats_left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        stats_right = ttk.Frame(stats_frame)
        stats_right.pack(side="right", fill="both", expand=True)
        
        # Left column statistics
        ttk.Label(stats_left, text="Total Accounts:", style='Stat.TLabel').pack(anchor="w")
        self.total_accounts_label = ttk.Label(stats_left, text="0", style='StatValue.TLabel')
        self.total_accounts_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_left, text="Active Accounts:", style='Stat.TLabel').pack(anchor="w")
        self.active_accounts_label = ttk.Label(stats_left, text="0", style='StatValue.TLabel')
        self.active_accounts_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_left, text="Total Portfolio Value:", style='Stat.TLabel').pack(anchor="w")
        self.total_value_label = ttk.Label(stats_left, text="$0.00", style='StatValue.TLabel')
        self.total_value_label.pack(anchor="w", pady=(0, 5))
        
        # Right column statistics
        ttk.Label(stats_right, text="Largest Account:", style='Stat.TLabel').pack(anchor="w")
        self.largest_account_label = ttk.Label(stats_right, text="--", style='StatValue.TLabel')
        self.largest_account_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_right, text="Average Account Value:", style='Stat.TLabel').pack(anchor="w")
        self.avg_account_value_label = ttk.Label(stats_right, text="$0.00", style='StatValue.TLabel')
        self.avg_account_value_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_right, text="Last Activity:", style='Stat.TLabel').pack(anchor="w")
        self.last_activity_label = ttk.Label(stats_right, text="--", style='StatValueSmall.TLabel')
        self.last_activity_label.pack(anchor="w", pady=(0, 5))
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(status_frame, text="Status:", style='Header.TLabel').pack(side="left")
        self.status_label = ttk.Label(status_frame, text="Ready", 
                                     style='Status.TLabel')
        self.status_label.pack(side="left", padx=(10, 0))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Create tabs
        self.create_accounts_tab()
        self.create_transfers_tab()
        self.create_trades_tab()
        self.create_overview_tab()
        
    def create_accounts_tab(self):
        """Create the accounts management tab"""
        accounts_frame = ttk.Frame(self.notebook)
        self.notebook.add(accounts_frame, text="Accounts")
        
        # Left panel - Account list
        left_panel = ttk.Frame(accounts_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Account list header
        list_header = ttk.Label(left_panel, text="Sub-Accounts", style='Header.TLabel')
        list_header.pack(pady=(0, 10))
        
        # Account listbox with scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill="both", expand=True)
        
        self.account_listbox = tk.Listbox(list_frame, height=15, font=('Arial', 10),
                                        bg="#3c3c3c", fg="#ffffff", selectbackground="#4a9eff")
        self.account_listbox.pack(side="left", fill="both", expand=True)
        self.account_listbox.bind('<<ListboxSelect>>', self.on_account_select)
        
        # Scrollbar for listbox
        list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.account_listbox.yview)
        list_scrollbar.pack(side="right", fill="y")
        self.account_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        # Right panel - Account details
        right_panel = ttk.Frame(accounts_frame)
        right_panel.pack(side="right", fill="both", expand=True)
        
        # Account details header
        details_header = ttk.Label(right_panel, text="Account Details", style='Header.TLabel')
        details_header.pack(pady=(0, 10))
        
        # Account details frame
        self.details_frame = ttk.Frame(right_panel)
        self.details_frame.pack(fill="both", expand=True)
        
        # Account info labels
        self.account_id_label = ttk.Label(self.details_frame, text="Account ID: ", style='Stat.TLabel')
        self.account_id_label.pack(anchor=tk.W, pady=2)
        
        self.nickname_label = ttk.Label(self.details_frame, text="Nickname: ", style='Stat.TLabel')
        self.nickname_label.pack(anchor=tk.W, pady=2)
        
        self.created_date_label = ttk.Label(self.details_frame, text="Created: ", style='Stat.TLabel')
        self.created_date_label.pack(anchor=tk.W, pady=2)
        
        self.active_label = ttk.Label(self.details_frame, text="Status: ", style='Stat.TLabel')
        self.active_label.pack(anchor=tk.W, pady=2)
        
        # Balances section
        balances_header = ttk.Label(self.details_frame, text="Balances", style='Header.TLabel')
        balances_header.pack(anchor=tk.W, pady=(20, 5))
        
        # Balances treeview
        tree_frame = ttk.Frame(self.details_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.balances_tree = ttk.Treeview(tree_frame, columns=('Asset', 'Balance'), 
                                        show='headings', height=8)
        self.balances_tree.heading('Asset', text='Asset')
        self.balances_tree.heading('Balance', text='Balance')
        self.balances_tree.column('Asset', width=100)
        self.balances_tree.column('Balance', width=150)
        self.balances_tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar for balances tree
        balances_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.balances_tree.yview)
        balances_scrollbar.pack(side="right", fill="y")
        self.balances_tree.configure(yscrollcommand=balances_scrollbar.set)
        
        # Edit balance button
        ttk.Button(self.details_frame, text="Edit Balance", 
                  command=self.edit_balance_dialog, style='Action.TButton').pack(pady=(10, 0))
        
    def create_transfers_tab(self):
        """Create the transfers tab"""
        transfers_frame = ttk.Frame(self.notebook)
        self.notebook.add(transfers_frame, text="Transfers")
        
        # Transfer form
        form_frame = ttk.LabelFrame(transfers_frame, text="Transfer Funds", padding="20")
        form_frame.pack(fill="x", padx=20, pady=20)
        
        # From account
        ttk.Label(form_frame, text="From Account:", style='Stat.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.from_account_var = tk.StringVar()
        self.from_account_combo = ttk.Combobox(form_frame, textvariable=self.from_account_var, 
                                              state="readonly", width=30)
        self.from_account_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # To account
        ttk.Label(form_frame, text="To Account:", style='Stat.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.to_account_var = tk.StringVar()
        self.to_account_combo = ttk.Combobox(form_frame, textvariable=self.to_account_var, 
                                            state="readonly", width=30)
        self.to_account_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Asset selection/input
        ttk.Label(form_frame, text="Asset:", style='Stat.TLabel').grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # Create frame for asset selection
        asset_frame = ttk.Frame(form_frame)
        asset_frame.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Common assets dropdown
        common_assets = ['ZUSD', 'ZEUR', 'XXBT', 'XETH', 'ADA', 'DOT', 'LINK', 'LTC', 'XRP']
        self.asset_var = tk.StringVar()
        
        self.asset_combo = ttk.Combobox(asset_frame, textvariable=self.asset_var, 
                                       values=common_assets, 
                                       state="readonly", width=15)
        self.asset_combo.pack(side="left", padx=(0, 10))
        
        # Custom asset entry
        ttk.Label(asset_frame, text="or Custom:", style='Stat.TLabel').pack(side="left", padx=(10, 5))
        self.custom_asset_var = tk.StringVar()
        custom_asset_entry = ttk.Entry(asset_frame, textvariable=self.custom_asset_var, width=10)
        custom_asset_entry.pack(side="left")
        
        # Amount
        ttk.Label(form_frame, text="Amount:", style='Stat.TLabel').grid(row=3, column=0, sticky=tk.W, pady=5)
        self.amount_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.amount_var, width=30).grid(row=3, column=1, 
                                                                          sticky=tk.W, pady=5, padx=(10, 0))
        
        # Transfer button
        ttk.Button(form_frame, text="Execute Transfer", 
                  command=self.execute_transfer, style='Primary.TButton').grid(row=4, column=0, columnspan=2, pady=20)
        
        # Transfer history
        history_frame = ttk.LabelFrame(transfers_frame, text="Transfer History", padding="20")
        history_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(history_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.transfer_tree = ttk.Treeview(tree_frame, 
                                        columns=('Date', 'From', 'To', 'Asset', 'Amount'), 
                                        show='headings', height=10)
        self.transfer_tree.heading('Date', text='Date')
        self.transfer_tree.heading('From', text='From Account')
        self.transfer_tree.heading('To', text='To Account')
        self.transfer_tree.heading('Asset', text='Asset')
        self.transfer_tree.heading('Amount', text='Amount')
        
        # Configure column widths
        self.transfer_tree.column('Date', width=150)
        self.transfer_tree.column('From', width=100)
        self.transfer_tree.column('To', width=100)
        self.transfer_tree.column('Asset', width=80)
        self.transfer_tree.column('Amount', width=100)
        
        self.transfer_tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar for transfer tree
        transfer_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.transfer_tree.yview)
        transfer_scrollbar.pack(side="right", fill="y")
        self.transfer_tree.configure(yscrollcommand=transfer_scrollbar.set)
        
    def create_trades_tab(self):
        """Create the trades tab"""
        trades_frame = ttk.Frame(self.notebook)
        self.notebook.add(trades_frame, text="Trades")
        
        # Trade form
        form_frame = ttk.LabelFrame(trades_frame, text="Post Trade", padding="20")
        form_frame.pack(fill="x", padx=20, pady=20)
        
        # Account selection
        ttk.Label(form_frame, text="Account:", style='Stat.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.trade_account_var = tk.StringVar()
        self.trade_account_combo = ttk.Combobox(form_frame, textvariable=self.trade_account_var, 
                                               state="readonly", width=30)
        self.trade_account_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Side (Buy/Sell)
        ttk.Label(form_frame, text="Side:", style='Stat.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.side_var = tk.StringVar()
        ttk.Radiobutton(form_frame, text="Buy", variable=self.side_var, value="BUY").grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        ttk.Radiobutton(form_frame, text="Sell", variable=self.side_var, value="SELL").grid(row=1, column=1, sticky=tk.W, pady=5, padx=(80, 0))
        
        # Trading pair
        ttk.Label(form_frame, text="Pair:", style='Stat.TLabel').grid(row=2, column=0, sticky=tk.W, pady=5)
        self.pair_var = tk.StringVar()
        self.pair_combo = ttk.Combobox(form_frame, textvariable=self.pair_var, 
                                      values=['XXBTZUSD', 'XETHZUSD', 'XXBTZEUR', 'XETHZEUR'], 
                                      state="readonly", width=30)
        self.pair_combo.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Quantity
        ttk.Label(form_frame, text="Quantity:", style='Stat.TLabel').grid(row=3, column=0, sticky=tk.W, pady=5)
        self.quantity_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.quantity_var, width=30).grid(row=3, column=1, 
                                                                            sticky=tk.W, pady=5, padx=(10, 0))
        
        # Price
        ttk.Label(form_frame, text="Price:", style='Stat.TLabel').grid(row=4, column=0, sticky=tk.W, pady=5)
        self.price_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.price_var, width=30).grid(row=4, column=1, 
                                                                         sticky=tk.W, pady=5, padx=(10, 0))
        
        # Post trade button
        ttk.Button(form_frame, text="Post Trade", 
                  command=self.post_trade, style='Primary.TButton').grid(row=5, column=0, columnspan=2, pady=20)
        
        # Trade history
        history_frame = ttk.LabelFrame(trades_frame, text="Trade History", padding="20")
        history_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(history_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.trade_tree = ttk.Treeview(tree_frame, 
                                     columns=('Date', 'Account', 'Side', 'Pair', 'Quantity', 'Price', 'Total'), 
                                     show='headings', height=10)
        self.trade_tree.heading('Date', text='Date')
        self.trade_tree.heading('Account', text='Account')
        self.trade_tree.heading('Side', text='Side')
        self.trade_tree.heading('Pair', text='Pair')
        self.trade_tree.heading('Quantity', text='Quantity')
        self.trade_tree.heading('Price', text='Price')
        self.trade_tree.heading('Total', text='Total Value')
        
        # Configure column widths
        self.trade_tree.column('Date', width=150)
        self.trade_tree.column('Account', width=80)
        self.trade_tree.column('Side', width=60)
        self.trade_tree.column('Pair', width=100)
        self.trade_tree.column('Quantity', width=80)
        self.trade_tree.column('Price', width=80)
        self.trade_tree.column('Total', width=100)
        
        self.trade_tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar for trade tree
        trade_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.trade_tree.yview)
        trade_scrollbar.pack(side="right", fill="y")
        self.trade_tree.configure(yscrollcommand=trade_scrollbar.set)
        
    def create_overview_tab(self):
        """Create the overview tab"""
        overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(overview_frame, text="Overview")
        
        # Account summary table
        table_frame = ttk.LabelFrame(overview_frame, text="Account Summary", padding="20")
        table_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(table_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.summary_tree = ttk.Treeview(tree_frame, 
                                       columns=('ID', 'Nickname', 'Status', 'Value', 'Last Activity'), 
                                       show='headings', height=15)
        self.summary_tree.heading('ID', text='Account ID')
        self.summary_tree.heading('Nickname', text='Nickname')
        self.summary_tree.heading('Status', text='Status')
        self.summary_tree.heading('Value', text='Portfolio Value')
        self.summary_tree.heading('Last Activity', text='Last Activity')
        
        # Configure column widths
        self.summary_tree.column('ID', width=100)
        self.summary_tree.column('Nickname', width=150)
        self.summary_tree.column('Status', width=80)
        self.summary_tree.column('Value', width=120)
        self.summary_tree.column('Last Activity', width=150)
        
        self.summary_tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar for summary tree
        summary_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.summary_tree.yview)
        summary_scrollbar.pack(side="right", fill="y")
        self.summary_tree.configure(yscrollcommand=summary_scrollbar.set)
        
    def on_account_select(self, event):
        """Handle account selection with async detail loading"""
        selection = self.account_listbox.curselection()
        if selection:
            account_text = self.account_listbox.get(selection[0])
            account_id = int(account_text.split(':')[0])
            self.selected_account_id = account_id
            
            # Load details asynchronously to prevent UI blocking
            self.async_display_account_details(account_id)
    
    def async_display_account_details(self, account_id: int):
        """Display account details asynchronously"""
        def load_details():
            return self.accounts_data.get(account_id)
        
        def on_details_loaded(future):
            try:
                account_data = future.result()
                if account_data:
                    self.root.after(0, self._update_account_details_ui, account_id, account_data)
            except Exception as e:
                print(f"Error loading account details: {e}")
        
        future = self.executor.submit(load_details)
        future.add_done_callback(on_details_loaded)
    
    def _update_account_details_ui(self, account_id: int, account_data: dict):
        """Update account details UI"""
        # Update labels
        self.account_id_label.config(text=f"Account ID: {account_id}")
        self.nickname_label.config(text=f"Nickname: {account_data.get('nick_name', 'N/A')}")
        self.created_date_label.config(text=f"Created: {account_data.get('created_date', 'N/A')}")
        self.active_label.config(text=f"Status: {'Active' if account_data.get('active', False) else 'Inactive'}")
        
        # Update balances tree
        for item in self.balances_tree.get_children():
            self.balances_tree.delete(item)
        
        balances = account_data.get('balances', {})
        for asset, balance in balances.items():
            self.balances_tree.insert('', tk.END, values=(asset, f"{balance:.8f}"))
    
    def display_account_details(self, account_id: int):
        """Legacy method for compatibility"""
        self.async_display_account_details(account_id)
        
    def create_account_dialog(self):
        """Dialog to create a new account"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Account")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#2b2b2b")
        
        # Form fields
        ttk.Label(dialog, text="Account ID:", style='Stat.TLabel').pack(pady=5)
        account_id_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=account_id_var).pack(pady=5)
        
        ttk.Label(dialog, text="Nickname:", style='Stat.TLabel').pack(pady=5)
        nickname_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=nickname_var).pack(pady=5)
        
        ttk.Label(dialog, text="Created Date:", style='Stat.TLabel').pack(pady=5)
        date_var = tk.StringVar(value=datetime.datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(dialog, textvariable=date_var).pack(pady=5)
        
        active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Active", variable=active_var).pack(pady=10)
        
        def create():
            try:
                account_id = int(account_id_var.get())
                nickname = nickname_var.get()
                created_date = date_var.get()
                active = active_var.get()
                
                account_edit = AccountEdit(account_id, nickname)
                account_edit.data['created_date'] = created_date
                account_edit.data['active'] = active
                
                filepath = account_edit.create_account()
                if filepath:
                    messagebox.showinfo("Success", f"Account created successfully!\nSaved to: {filepath}")
                    dialog.destroy()
                    self.async_load_accounts()  # Refresh the account list (without fetching prices)
                else:
                    messagebox.showerror("Error", "Failed to create account")
            except ValueError:
                messagebox.showerror("Error", "Account ID must be a number")
        
        ttk.Button(dialog, text="Create", command=create, style='Primary.TButton').pack(pady=20)
        
    def delete_account(self):
        """Delete selected account"""
        if self.selected_account_id is None:
            messagebox.showwarning("Warning", "Please select an account to delete")
            return
        
        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete account {self.selected_account_id}?"):
            account_edit = AccountEdit(self.selected_account_id)
            if account_edit.delete_account():
                messagebox.showinfo("Success", "Account deleted successfully")
                self.selected_account_id = None
                self.async_load_accounts()  # Refresh the account list (without fetching prices)
            else:
                messagebox.showerror("Error", "Failed to delete account")
        
    def edit_balance_dialog(self):
        """Dialog to edit account balance"""
        if self.selected_account_id is None:
            messagebox.showwarning("Warning", "Please select an account first")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Balance")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#2b2b2b")
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Edit Account Balances", style='Header.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Current balances display
        current_frame = ttk.LabelFrame(main_frame, text="Current Balances", padding="10")
        current_frame.pack(fill="x", pady=(0, 20))
        
        # Get current balances
        account_data = self.accounts_data[self.selected_account_id]
        current_balances = account_data.get('balances', {})
        
        # Display current balances
        if current_balances:
            for asset, balance in current_balances.items():
                balance_label = ttk.Label(current_frame, 
                                        text=f"{asset}: {balance:.8f}", 
                                        style='Stat.TLabel')
                balance_label.pack(anchor="w", pady=2)
        else:
            no_balance_label = ttk.Label(current_frame, 
                                       text="No balances found", 
                                       style='Stat.TLabel')
            no_balance_label.pack(anchor="w", pady=2)
        
        # Edit section
        edit_frame = ttk.LabelFrame(main_frame, text="Add/Edit Balance", padding="10")
        edit_frame.pack(fill="x", pady=(0, 20))
        
        # Asset selection/input
        ttk.Label(edit_frame, text="Asset:", style='Stat.TLabel').pack(anchor="w", pady=(0, 5))
        
        # Create frame for asset selection
        asset_frame = ttk.Frame(edit_frame)
        asset_frame.pack(fill="x", pady=(0, 10))
        
        # Common assets dropdown
        common_assets = ['ZUSD', 'ZEUR', 'XXBT', 'XETH', 'ADA', 'DOT', 'LINK', 'LTC', 'XRP']
        asset_var = tk.StringVar()
        
        # Add current assets to the list
        all_assets = list(set(common_assets + list(current_balances.keys())))
        all_assets.sort()
        
        asset_combo = ttk.Combobox(asset_frame, textvariable=asset_var, 
                                  values=all_assets, 
                                  state="readonly", width=15)
        asset_combo.pack(side="left", padx=(0, 10))
        
        # Custom asset entry
        ttk.Label(asset_frame, text="or Custom:", style='Stat.TLabel').pack(side="left", padx=(10, 5))
        custom_asset_var = tk.StringVar()
        custom_asset_entry = ttk.Entry(asset_frame, textvariable=custom_asset_var, width=10)
        custom_asset_entry.pack(side="left")
        
        # Amount
        ttk.Label(edit_frame, text="Amount:", style='Stat.TLabel').pack(anchor="w", pady=(10, 5))
        amount_var = tk.StringVar()
        amount_entry = ttk.Entry(edit_frame, textvariable=amount_var, width=20)
        amount_entry.pack(anchor="w", pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ttk.Frame(edit_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        def save():
            try:
                # Determine which asset to use
                asset = asset_var.get() if asset_var.get() else custom_asset_var.get()
                if not asset:
                    messagebox.showerror("Error", "Please select or enter an asset")
                    return
                
                amount = float(amount_var.get())
                
                # Update the account data
                account_data = self.accounts_data[self.selected_account_id].copy()
                if 'balances' not in account_data:
                    account_data['balances'] = {}
                
                # Add or update the balance
                account_data['balances'][asset] = amount
                
                # Save using AccountEdit
                account_edit = AccountEdit(self.selected_account_id)
                if account_edit.edit_account_balance(account_data['balances']):
                    messagebox.showinfo("Success", f"Balance updated: {asset} = {amount}")
                    # Update local cache
                    self.accounts_data[self.selected_account_id] = account_data
                    self.display_account_details(self.selected_account_id)
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to update balance")
            except ValueError:
                messagebox.showerror("Error", "Amount must be a valid number")
        
        def clear_form():
            asset_var.set('')
            custom_asset_var.set('')
            amount_var.set('')
        
        # Save and Clear buttons
        ttk.Button(buttons_frame, text="Save", command=save, 
                  style='Primary.TButton').pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="Clear", command=clear_form, 
                  style='Action.TButton').pack(side="left")
        
        # Instructions
        instructions_frame = ttk.LabelFrame(main_frame, text="Instructions", padding="10")
        instructions_frame.pack(fill="x")
        
        instructions_text = """• Select an existing asset from the dropdown or enter a custom asset name
• Enter the new balance amount
• Click Save to update the account balance
• The balance will be added or updated for the selected asset"""
        
        instructions_label = ttk.Label(instructions_frame, text=instructions_text, 
                                     style='Stat.TLabel', wraplength=450)
        instructions_label.pack(anchor="w")
        
    def execute_transfer(self):
        """Execute fund transfer between accounts"""
        try:
            from_account = int(self.from_account_var.get().split(':')[0])
            to_account = int(self.to_account_var.get().split(':')[0])
            
            # Determine which asset to use (dropdown or custom)
            asset = self.asset_var.get() if self.asset_var.get() else self.custom_asset_var.get()
            if not asset:
                messagebox.showerror("Error", "Please select or enter an asset")
                return
                
            amount = float(self.amount_var.get())
            
            if self.sub_account_manager.transfer_funds(from_account, to_account, asset, amount):
                messagebox.showinfo("Success", f"Transfer executed successfully: {amount} {asset}")
                # Clear form
                self.from_account_var.set('')
                self.to_account_var.set('')
                self.asset_var.set('')
                self.custom_asset_var.set('')
                self.amount_var.set('')
                # Refresh accounts to update balances (without fetching prices)
                self.async_load_accounts()
            else:
                messagebox.showerror("Error", "Transfer failed")
        except (ValueError, IndexError):
            messagebox.showerror("Error", "Please fill all fields correctly")
        
    def post_trade(self):
        """Post a trade to an account"""
        try:
            account_id = int(self.trade_account_var.get().split(':')[0])
            side = self.side_var.get()
            pair = self.pair_var.get()
            quantity = float(self.quantity_var.get())
            price = float(self.price_var.get())
            
            if self.sub_account_manager.post_trade(side, pair, quantity, price, account_id):
                messagebox.showinfo("Success", "Trade posted successfully")
                # Clear form
                self.trade_account_var.set('')
                self.side_var.set('')
                self.pair_var.set('')
                self.quantity_var.set('')
                self.price_var.set('')
                # Refresh accounts to update balances (without fetching prices)
                self.async_load_accounts()
            else:
                messagebox.showerror("Error", "Trade posting failed")
        except (ValueError, IndexError):
            messagebox.showerror("Error", "Please fill all fields correctly")

    def update_overview(self):
        """Legacy method for compatibility - delegates to async version"""
        self.async_update_overview()

    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

def main():
    """Main function to run the UI"""
    root = tk.Tk()
    app = SubAccountUI(root)
    
    # Ensure proper cleanup on window close
    def on_closing():
        if hasattr(app, 'executor'):
            app.executor.shutdown(wait=False)
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()