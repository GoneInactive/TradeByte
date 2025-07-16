import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "clients")))
from kraken_python_client import KrakenPythonClient
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
from datetime import datetime
import pandas as pd

class TradeByteCriteriaFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()
    
    def create_widgets(self):
        # Main criteria frame
        criteria_frame = ttk.LabelFrame(self, text="Scanning Criteria", padding="10")
        criteria_frame.pack(fill="x", pady=(0, 10))
        
        # Spread criteria
        spread_frame = ttk.Frame(criteria_frame)
        spread_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(spread_frame, text="Spread Range (%):").pack(side="left")
        self.min_spread_var = tk.StringVar(value="0.01")
        min_spread_entry = ttk.Entry(spread_frame, textvariable=self.min_spread_var, width=8)
        min_spread_entry.pack(side="left", padx=(5, 2))
        ttk.Label(spread_frame, text="to").pack(side="left", padx=(2, 2))
        self.max_spread_var = tk.StringVar(value="0.5")
        max_spread_entry = ttk.Entry(spread_frame, textvariable=self.max_spread_var, width=8)
        max_spread_entry.pack(side="left", padx=(2, 0))
        
        # Volume criteria
        volume_frame = ttk.Frame(criteria_frame)
        volume_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(volume_frame, text="Min Volume (24h):").pack(side="left")
        self.volume_var = tk.StringVar(value="1000")
        volume_entry = ttk.Entry(volume_frame, textvariable=self.volume_var, width=10)
        volume_entry.pack(side="left", padx=(5, 0))
        
        # Price range criteria
        price_frame = ttk.Frame(criteria_frame)
        price_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(price_frame, text="Price Range:").pack(side="left")
        self.min_price_var = tk.StringVar(value="0.01")
        ttk.Entry(price_frame, textvariable=self.min_price_var, width=8).pack(side="left", padx=(5, 2))
        ttk.Label(price_frame, text="to").pack(side="left", padx=(2, 2))
        self.max_price_var = tk.StringVar(value="100000")
        ttk.Entry(price_frame, textvariable=self.max_price_var, width=8).pack(side="left", padx=(2, 0))
        
        # Asset type filter
        asset_frame = ttk.Frame(criteria_frame)
        asset_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(asset_frame, text="Asset Type:").pack(side="left")
        self.asset_type_var = tk.StringVar(value="All")
        asset_combo = ttk.Combobox(asset_frame, textvariable=self.asset_type_var, 
                                  values=["All", "USD", "EUR", "GBP", "JPY", "CAD", "AUD"])
        asset_combo.pack(side="left", padx=(5, 0))
        asset_combo.state(['readonly'])

class TradeByteScannerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TradeByte Kraken Scanner")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # Initialize Kraken client
        self.kraken_client = KrakenPythonClient(error_message=True)
        
        # Scanner state
        self.is_scanning = False
        self.scan_thread = None
        self.scan_results = []
        
        # Setup GUI
        self.setup_styles()
        self.create_widgets()
        
        # Test connection on startup
        self.test_connection()
    
    def setup_styles(self):
        # Configure modern dark theme with gradients and better colors
        style = ttk.Style()
        style.theme_use('clam')
        
        # Modern color palette
        bg_primary = "#1e1e1e"      # Dark background
        bg_secondary = "#2d2d2d"    # Lighter dark
        bg_accent = "#3d3d3d"       # Accent background
        fg_primary = "#ffffff"      # White text
        fg_secondary = "#b0b0b0"    # Light gray text
        accent_blue = "#007acc"     # Modern blue
        accent_green = "#28a745"    # Success green
        accent_red = "#dc3545"      # Error red
        accent_orange = "#fd7e14"   # Warning orange
        
        self.root.configure(bg=bg_primary)
        
        # Title and headers
        style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'), 
                       background=bg_primary, foreground=fg_primary)
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'), 
                       background=bg_primary, foreground=fg_primary)
        style.configure('SubHeader.TLabel', font=('Segoe UI', 10, 'bold'), 
                       background=bg_primary, foreground=fg_secondary)
        style.configure('Status.TLabel', font=('Segoe UI', 10), 
                       background=bg_primary, foreground=accent_blue)
        
        # Frames and containers
        style.configure('TFrame', background=bg_primary)
        style.configure('TLabelframe', background=bg_primary, foreground=fg_primary,
                       borderwidth=2, relief='solid')
        style.configure('TLabelframe.Label', background=bg_primary, foreground=fg_primary,
                       font=('Segoe UI', 11, 'bold'))
        
        # Entries
        style.configure('TEntry', fieldbackground=bg_secondary, foreground=fg_primary,
                       borderwidth=1, relief='solid', insertcolor=fg_primary)
        style.map('TEntry', focuscolor=[('focus', accent_blue)])
        
        # Combobox
        style.configure('TCombobox', fieldbackground=bg_secondary, foreground=fg_primary,
                       borderwidth=1, relief='solid', arrowcolor=fg_primary)
        style.map('TCombobox', fieldbackground=[('readonly', bg_secondary)])
        
        # Treeview with modern styling
        style.configure('Treeview', background=bg_secondary, 
                       foreground=fg_primary, fieldbackground=bg_secondary,
                       borderwidth=1, relief='solid')
        style.configure('Treeview.Heading', background=bg_accent, 
                       foreground=fg_primary, font=('Segoe UI', 10, 'bold'),
                       relief='raised', borderwidth=1)
        style.map('Treeview.Heading', background=[('active', accent_blue)])
        style.map('Treeview', background=[('selected', accent_blue)])
        
        # Buttons with modern styling
        style.configure('Scan.TButton', font=('Segoe UI', 11, 'bold'),
                       background=accent_green, foreground='white', borderwidth=0,
                       focuscolor='none', padding=(20, 8))
        style.map('Scan.TButton', 
                 background=[('active', '#218838'), ('pressed', '#1e7e34')])
        
        style.configure('Stop.TButton', font=('Segoe UI', 11, 'bold'),
                       background=accent_red, foreground='white', borderwidth=0,
                       focuscolor='none', padding=(20, 8))
        style.map('Stop.TButton', 
                 background=[('active', '#c82333'), ('pressed', '#bd2130')])
        
        style.configure('Action.TButton', font=('Segoe UI', 10),
                       background=accent_blue, foreground='white', borderwidth=0,
                       focuscolor='none', padding=(15, 6))
        style.map('Action.TButton', 
                 background=[('active', '#0056b3'), ('pressed', '#004085')])
        
        # Progress bar
        style.configure('TProgressbar', background=accent_blue, 
                       troughcolor=bg_secondary, borderwidth=1, relief='solid')
        
        # Labels for better text hierarchy
        style.configure('Accent.TLabel', font=('Segoe UI', 10), 
                       background=bg_primary, foreground=accent_blue)
        style.configure('Success.TLabel', font=('Segoe UI', 10), 
                       background=bg_primary, foreground=accent_green)
        style.configure('Error.TLabel', font=('Segoe UI', 10), 
                       background=bg_primary, foreground=accent_red)
    
    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="25")
        main_frame.pack(fill="both", expand=True)
        
        # Header with modern styling
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 25))
        
        # Title with icon-like styling
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side="left")
        
        title_label = ttk.Label(title_frame, text="⚡ TradeByte", 
                               style='Title.TLabel')
        title_label.pack(side="left")
        
        subtitle_label = ttk.Label(title_frame, text="Kraken Scanner", 
                                  style='SubHeader.TLabel')
        subtitle_label.pack(side="left", padx=(10, 0))
        
        # Connection status with better styling
        status_frame = ttk.Frame(header_frame)
        status_frame.pack(side="right")
        
        ttk.Label(status_frame, text="Connection:", style='SubHeader.TLabel').pack(side="left")
        self.connection_status = ttk.Label(status_frame, text="● Disconnected", 
                                         style='Error.TLabel')
        self.connection_status.pack(side="left", padx=(5, 0))
        
        # Top panel with better spacing
        top_panel = ttk.Frame(main_frame)
        top_panel.pack(fill="x", pady=(0, 25))
        
        # Left side - Criteria (wider)
        left_panel = ttk.Frame(top_panel)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 20))
        
        self.criteria_frame = TradeByteCriteriaFrame(left_panel)
        self.criteria_frame.pack(fill="x")
        
        # Right side - Controls (fixed width)
        control_frame = ttk.LabelFrame(top_panel, text="🎯 Scanner Controls", padding="15")
        control_frame.pack(side="right", fill="y", ipadx=10)
        
        # Scan button with dynamic styling
        self.scan_button = ttk.Button(control_frame, text="🚀 Start Scan", 
                                     command=self.toggle_scan, style='Scan.TButton')
        self.scan_button.pack(pady=(0, 12), fill="x")
        
        # Export button
        export_button = ttk.Button(control_frame, text="📊 Export Results", 
                                  command=self.export_results, style='Action.TButton')
        export_button.pack(pady=(0, 12), fill="x")
        
        # Clear button
        clear_button = ttk.Button(control_frame, text="🗑 Clear Results", 
                                 command=self.clear_results, style='Action.TButton')
        clear_button.pack(fill="x")
        
        # Scanner status with better layout
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(0, 15))
        
        status_left = ttk.Frame(status_frame)
        status_left.pack(side="left", fill="x", expand=True)
        
        ttk.Label(status_left, text="Status:", style='Header.TLabel').pack(side="left")
        self.status_label = ttk.Label(status_left, text="Ready to scan", 
                                     style='Accent.TLabel')
        self.status_label.pack(side="left", padx=(10, 0))
        
        # Progress bar with better styling
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(progress_frame, text="Progress:", style='SubHeader.TLabel').pack(anchor="w")
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          mode='determinate', style='TProgressbar')
        self.progress_bar.pack(fill="x", pady=(5, 0))
        
        # Results table with enhanced styling
        self.create_results_table(main_frame)
    
    def create_results_table(self, parent):
        # Table frame with modern styling
        table_frame = ttk.LabelFrame(parent, text="📈 Scan Results", padding="15")
        table_frame.pack(fill="both", expand=True)
        
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(table_frame)
        tree_frame.pack(fill="both", expand=True)
        
        # Define columns with better names
        columns = ('Asset', 'Bid', 'Ask', 'Spread', 'Spread%', 'Volume', 'Score')
        
        self.results_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=16)
        
        # Configure column headings and widths with better alignment
        column_configs = {
            'Asset': {'width': 120, 'anchor': 'center'},
            'Bid': {'width': 140, 'anchor': 'e'},
            'Ask': {'width': 140, 'anchor': 'e'},
            'Spread': {'width': 120, 'anchor': 'e'},
            'Spread%': {'width': 100, 'anchor': 'center'},
            'Volume': {'width': 140, 'anchor': 'e'},
            'Score': {'width': 100, 'anchor': 'center'}
        }
        
        for col in columns:
            config = column_configs[col]
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=config['width'], anchor=config['anchor'])
        
        # Scrollbars with better styling
        scrollbar_frame = ttk.Frame(tree_frame)
        scrollbar_frame.pack(side="right", fill="y")
        
        v_scrollbar = ttk.Scrollbar(scrollbar_frame, orient="vertical", command=self.results_tree.yview)
        v_scrollbar.pack(fill="y")
        
        self.results_tree.configure(yscrollcommand=v_scrollbar.set)
        self.results_tree.pack(side="left", fill="both", expand=True)
        
        # Results summary with better styling
        summary_frame = ttk.Frame(table_frame)
        summary_frame.pack(fill="x", pady=(15, 0))
        
        # Left side - Results count
        summary_left = ttk.Frame(summary_frame)
        summary_left.pack(side="left")
        
        ttk.Label(summary_left, text="📊", style='Header.TLabel').pack(side="left")
        self.results_count_label = ttk.Label(summary_left, text="Results: 0", 
                                           style='Header.TLabel')
        self.results_count_label.pack(side="left", padx=(5, 0))
        
        # Right side - Last scan time
        summary_right = ttk.Frame(summary_frame)
        summary_right.pack(side="right")
        
        ttk.Label(summary_right, text="🕐", style='SubHeader.TLabel').pack(side="left")
        self.last_scan_label = ttk.Label(summary_right, text="Last scan: Never", 
                                        style='SubHeader.TLabel')
        self.last_scan_label.pack(side="left", padx=(5, 0))
    
    def test_connection(self):
        """Test connection to Kraken API"""
        try:
            if self.kraken_client.test_connection():
                self.connection_status.config(text="● Connected", style="Success.TLabel")
                self.update_status("Connected to Kraken API")
            else:
                self.connection_status.config(text="● Disconnected", style="Error.TLabel")
                self.update_status("Failed to connect to Kraken API")
        except Exception as e:
            self.connection_status.config(text="● Error", style="Error.TLabel")
            self.update_status(f"Connection error: {str(e)}")
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def get_all_kraken_assets(self):
        """Get list of all tradeable assets from Kraken"""
        # Since we don't have direct access to asset info endpoint,
        # we'll use a predefined list of common Kraken trading pairs
        common_pairs = [
            'XBTUSD', 'ETHUSD', 'ADAUSD', 'DOTUSD', 'LINKUSD',
            'LTCUSD', 'XRPUSD', 'BCHUSD', 'UNIUSD', 'AAVEUSD',
            'MATICUSD', 'ATOMUSD', 'ALGOUSD', 'FILUSD', 'TRXUSD',
            'XBTEUR', 'ETHEUR', 'ADAEUR', 'DOTEUR', 'LINKEUR',
            'LTCEUR', 'XRPEUR', 'BCHEUR', 'UNIEUR', 'AAVEEUR',
            'XBTGBP', 'ETHGBP', 'XBTJPY', 'ETHJPY', 'XBTCAD',
            'ETHCAD', 'XBTAUD', 'ETHAUD'
        ]
        
        # Filter based on asset type selection
        asset_type = self.criteria_frame.asset_type_var.get()
        if asset_type != "All":
            filtered_pairs = [pair for pair in common_pairs if pair.endswith(asset_type)]
            return filtered_pairs
        
        return common_pairs
    
    def calculate_score(self, spread_pct, volume, bid_price):
        """Calculate a score for the asset based on criteria"""
        score = 0
        
        # Spread score (lower is better)
        if spread_pct < 0.1:
            score += 50
        elif spread_pct < 0.25:
            score += 30
        elif spread_pct < 0.5:
            score += 10
        
        # Volume score (higher is better)
        if volume > 10000:
            score += 30
        elif volume > 5000:
            score += 20
        elif volume > 1000:
            score += 10
        
        # Price stability score (avoid extreme prices)
        if 1 < bid_price < 1000:
            score += 20
        elif 0.1 < bid_price < 10000:
            score += 10
        
        return min(score, 100)  # Cap at 100
    
    def scan_asset(self, asset):
        """Scan a single asset and return results"""
        try:
            # Get bid and ask prices
            bid = self.kraken_client.get_bid(asset)
            ask = self.kraken_client.get_ask(asset)
            
            if not bid or not ask:
                return None
            
            # Convert to float
            bid_price = float(bid)
            ask_price = float(ask)
            
            # Calculate spread
            spread = ask_price - bid_price
            spread_pct = (spread / bid_price) * 100 if bid_price > 0 else 0
            
            # Get spread data (volume approximation)
            spread_data = self.kraken_client.get_spread(asset)
            volume = 5000  # Default volume since we don't have direct access
            
            # Apply criteria filters
            min_spread = float(self.criteria_frame.min_spread_var.get())
            max_spread = float(self.criteria_frame.max_spread_var.get())
            min_volume = float(self.criteria_frame.volume_var.get())
            min_price = float(self.criteria_frame.min_price_var.get())
            max_price = float(self.criteria_frame.max_price_var.get())
            
            # Check if asset meets criteria
            if (min_spread <= spread_pct <= max_spread and 
                volume >= min_volume and 
                min_price <= bid_price <= max_price):
                
                # Calculate score
                score = self.calculate_score(spread_pct, volume, bid_price)
                
                return {
                    'asset': asset,
                    'bid': bid_price,
                    'ask': ask_price,
                    'spread': spread,
                    'spread_pct': spread_pct,
                    'volume': volume,
                    'score': score
                }
            
            return None
            
        except Exception as e:
            print(f"Error scanning {asset}: {e}")
            return None
    
    def scan_worker(self):
        """Worker thread for scanning assets"""
        assets = self.get_all_kraken_assets()
        total_assets = len(assets)
        
        self.scan_results = []
        
        for i, asset in enumerate(assets):
            if not self.is_scanning:
                break
            
            self.update_status(f"Scanning {asset}... ({i+1}/{total_assets})")
            
            # Update progress
            progress = (i + 1) / total_assets * 100
            self.progress_var.set(progress)
            
            # Scan asset
            result = self.scan_asset(asset)
            if result:
                self.scan_results.append(result)
                
                # Update results table in real-time
                self.root.after(0, self.add_result_to_table, result)
            
            # Small delay to prevent API rate limiting
            time.sleep(0.1)
        
        # Sort results by score (highest first)
        self.scan_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Update UI when done
        self.root.after(0, self.scan_completed)
    
    def add_result_to_table(self, result):
        """Add a single result to the table"""
        values = (
            result['asset'],
            f"{result['bid']:.4f}",
            f"{result['ask']:.4f}",
            f"{result['spread']:.4f}",
            f"{result['spread_pct']:.2f}%",
            f"{result['volume']:.0f}",
            f"{result['score']:.0f}"
        )
        
        self.results_tree.insert('', 'end', values=values)
        self.results_count_label.config(text=f"Results: {len(self.scan_results)}")
    
    def scan_completed(self):
        """Handle scan completion"""
        self.is_scanning = False
        self.scan_button.config(text="🚀 Start Scan", style="Scan.TButton")
        self.progress_var.set(0)
        
        # Update status and timestamp
        self.update_status(f"Scan completed. Found {len(self.scan_results)} matching assets.")
        self.last_scan_label.config(text=f"Last scan: {datetime.now().strftime('%H:%M:%S')}")
        
        # Refresh the table with sorted results
        self.refresh_results_table()
    
    def refresh_results_table(self):
        """Refresh the results table with sorted data"""
        # Clear existing items
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Add sorted results
        for result in self.scan_results:
            self.add_result_to_table(result)
    
    def toggle_scan(self):
        """Start or stop scanning"""
        if not self.is_scanning:
            # Start scanning
            self.is_scanning = True
            self.scan_button.config(text="⏹ Stop Scan", style="Stop.TButton")
            self.clear_results()
            
            # Start scan thread
            self.scan_thread = threading.Thread(target=self.scan_worker)
            self.scan_thread.daemon = True
            self.scan_thread.start()
        else:
            # Stop scanning
            self.is_scanning = False
            self.scan_button.config(text="🚀 Start Scan", style="Scan.TButton")
            self.update_status("Scan stopped by user")
            self.progress_var.set(0)
    
    def clear_results(self):
        """Clear all scan results"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        self.scan_results = []
        self.results_count_label.config(text="Results: 0")
    
    def export_results(self):
        """Export scan results to CSV"""
        if not self.scan_results:
            messagebox.showwarning("No Results", "No scan results to export.")
            return
        
        try:
            # Create DataFrame
            df = pd.DataFrame(self.scan_results)
            
            # Save to CSV
            filename = f"kraken_scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            
            messagebox.showinfo("Export Successful", f"Results exported to {filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = TradeByteScannerGUI()
    app.run()