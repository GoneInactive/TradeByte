##
## GUI Version For SmartExecution
##
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import os
from datetime import datetime
import json

# Import the SmartTrader
from execution_trader import SmartTrader

class SmartTraderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TradeByte Trading Suite")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Initialize SmartTrader
        self.smart_trader = None
        self.initialize_trader()
        
        # Style configuration
        self.setup_styles()
        
        # Create main layout
        self.create_main_layout()
        
        # Auto-refresh prices every 5 seconds
        self.auto_refresh_active = False
        self.start_auto_refresh()
        
    def setup_styles(self):
        """Configure the styling for the GUI"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#2b2b2b', foreground='white')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), background='#2b2b2b', foreground='white')
        style.configure('Custom.TFrame', background='#2b2b2b')
        style.configure('Custom.TLabel', background='#2b2b2b', foreground='white')
        style.configure('Custom.TButton', font=('Arial', 10, 'bold'))
        
    def initialize_trader(self):
        """Initialize the SmartTrader instance"""
        try:
            self.smart_trader = SmartTrader()
            self.connection_status = "Connected" if self.smart_trader.exchanges_tradable else "Disconnected"
        except Exception as e:
            self.connection_status = f"Error: {str(e)}"
            messagebox.showerror("Connection Error", f"Failed to initialize SmartTrader: {str(e)}")
    
    def create_main_layout(self):
        """Create the main GUI layout"""
        # Create main container
        main_frame = ttk.Frame(self.root, style='Custom.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="Smart Trading Suite", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_trader_tab()
        self.create_market_data_tab()
        self.create_settings_tab()
        self.create_future_modules_tab()
        
        # Status bar
        self.create_status_bar(main_frame)
        
    def create_trader_tab(self):
        """Create the main trading tab"""
        trader_frame = ttk.Frame(self.notebook, style='Custom.TFrame')
        self.notebook.add(trader_frame, text="Smart Trader")
        
        # Connection status
        status_frame = ttk.Frame(trader_frame, style='Custom.TFrame')
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(status_frame, text="Connection Status:", style='Header.TLabel').pack(side=tk.LEFT)
        self.status_label = ttk.Label(status_frame, text=self.connection_status, style='Custom.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Trading form
        form_frame = ttk.LabelFrame(trader_frame, text="Execute Smart Market Order", padding=20)
        form_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Trading pair
        ttk.Label(form_frame, text="Trading Pair:", style='Custom.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pair_var = tk.StringVar(value="XBTUSD")
        pair_entry = ttk.Entry(form_frame, textvariable=self.pair_var, width=15)
        pair_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Side selection
        ttk.Label(form_frame, text="Side:", style='Custom.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.side_var = tk.StringVar(value="buy")
        side_frame = ttk.Frame(form_frame)
        side_frame.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        ttk.Radiobutton(side_frame, text="Buy", variable=self.side_var, value="buy").pack(side=tk.LEFT)
        ttk.Radiobutton(side_frame, text="Sell", variable=self.side_var, value="sell").pack(side=tk.LEFT, padx=(20, 0))
        
        # Quantity
        ttk.Label(form_frame, text="Quantity:", style='Custom.TLabel').grid(row=2, column=0, sticky=tk.W, pady=5)
        self.quantity_var = tk.StringVar(value="0.001")
        quantity_entry = ttk.Entry(form_frame, textvariable=self.quantity_var, width=15)
        quantity_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Threshold
        ttk.Label(form_frame, text="Threshold (bp):", style='Custom.TLabel').grid(row=3, column=0, sticky=tk.W, pady=5)
        self.threshold_var = tk.StringVar(value="10.00")
        threshold_entry = ttk.Entry(form_frame, textvariable=self.threshold_var, width=15)
        threshold_entry.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Execute button
        execute_btn = ttk.Button(form_frame, text="Execute Smart Order", command=self.execute_order, style='Custom.TButton')
        execute_btn.grid(row=4, column=0, columnspan=2, pady=20)
        
        # Results area
        results_frame = ttk.LabelFrame(trader_frame, text="Execution Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=15, bg='#1e1e1e', fg='white', font=('Courier', 10))
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
    def create_market_data_tab(self):
        """Create the market data tab"""
        market_frame = ttk.Frame(self.notebook, style='Custom.TFrame')
        self.notebook.add(market_frame, text="Market Data")
        
        # Controls
        controls_frame = ttk.Frame(market_frame, style='Custom.TFrame')
        controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(controls_frame, text="Pair:", style='Custom.TLabel').pack(side=tk.LEFT)
        self.market_pair_var = tk.StringVar(value="XBTUSD")
        market_pair_entry = ttk.Entry(controls_frame, textvariable=self.market_pair_var, width=15)
        market_pair_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        refresh_btn = ttk.Button(controls_frame, text="Refresh", command=self.refresh_market_data)
        refresh_btn.pack(side=tk.LEFT, padx=(20, 0))
        
        # Auto-refresh toggle
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = ttk.Checkbutton(controls_frame, text="Auto-refresh (5s)", variable=self.auto_refresh_var, command=self.toggle_auto_refresh)
        auto_refresh_cb.pack(side=tk.LEFT, padx=(20, 0))
        
        # Market data display
        data_frame = ttk.LabelFrame(market_frame, text="Live Market Data", padding=20)
        data_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Create grid for market data
        self.create_market_data_grid(data_frame)
        
        # Price chart placeholder
        chart_frame = ttk.LabelFrame(market_frame, text="Price Information", padding=20)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chart_text = scrolledtext.ScrolledText(chart_frame, height=10, bg='#1e1e1e', fg='white', font=('Courier', 10))
        self.chart_text.pack(fill=tk.BOTH, expand=True)
        
    def create_market_data_grid(self, parent):
        """Create the market data grid"""
        # Headers
        headers = ["Metric", "Value", "Status"]
        for i, header in enumerate(headers):
            ttk.Label(parent, text=header, style='Header.TLabel').grid(row=0, column=i, padx=10, pady=5, sticky=tk.W)
        
        # Data rows
        self.bid_label = ttk.Label(parent, text="--", style='Custom.TLabel')
        self.bid_label.grid(row=1, column=1, padx=10, pady=2, sticky=tk.W)
        ttk.Label(parent, text="Bid:", style='Custom.TLabel').grid(row=1, column=0, padx=10, pady=2, sticky=tk.W)
        self.bid_status = ttk.Label(parent, text="--", style='Custom.TLabel')
        self.bid_status.grid(row=1, column=2, padx=10, pady=2, sticky=tk.W)
        
        self.ask_label = ttk.Label(parent, text="--", style='Custom.TLabel')
        self.ask_label.grid(row=2, column=1, padx=10, pady=2, sticky=tk.W)
        ttk.Label(parent, text="Ask:", style='Custom.TLabel').grid(row=2, column=0, padx=10, pady=2, sticky=tk.W)
        self.ask_status = ttk.Label(parent, text="--", style='Custom.TLabel')
        self.ask_status.grid(row=2, column=2, padx=10, pady=2, sticky=tk.W)
        
        self.spread_label = ttk.Label(parent, text="--", style='Custom.TLabel')
        self.spread_label.grid(row=3, column=1, padx=10, pady=2, sticky=tk.W)
        ttk.Label(parent, text="Spread (bp):", style='Custom.TLabel').grid(row=3, column=0, padx=10, pady=2, sticky=tk.W)
        self.spread_status = ttk.Label(parent, text="--", style='Custom.TLabel')
        self.spread_status.grid(row=3, column=2, padx=10, pady=2, sticky=tk.W)
        
        self.mid_label = ttk.Label(parent, text="--", style='Custom.TLabel')
        self.mid_label.grid(row=4, column=1, padx=10, pady=2, sticky=tk.W)
        ttk.Label(parent, text="Mid Price:", style='Custom.TLabel').grid(row=4, column=0, padx=10, pady=2, sticky=tk.W)
        self.mid_status = ttk.Label(parent, text="--", style='Custom.TLabel')
        self.mid_status.grid(row=4, column=2, padx=10, pady=2, sticky=tk.W)
        
    def create_settings_tab(self):
        """Create the settings tab"""
        settings_frame = ttk.Frame(self.notebook, style='Custom.TFrame')
        self.notebook.add(settings_frame, text="Settings")
        
        # Connection settings
        conn_frame = ttk.LabelFrame(settings_frame, text="Connection Settings", padding=20)
        conn_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(conn_frame, text="Exchange:", style='Custom.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.exchange_var = tk.StringVar(value="Kraken")
        exchange_combo = ttk.Combobox(conn_frame, textvariable=self.exchange_var, values=["Kraken"], state="readonly")
        exchange_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        reconnect_btn = ttk.Button(conn_frame, text="Reconnect", command=self.reconnect_trader)
        reconnect_btn.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Trading settings
        trading_frame = ttk.LabelFrame(settings_frame, text="Default Trading Settings", padding=20)
        trading_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(trading_frame, text="Default Pair:", style='Custom.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.default_pair_var = tk.StringVar(value="XBTUSD")
        default_pair_entry = ttk.Entry(trading_frame, textvariable=self.default_pair_var, width=15)
        default_pair_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Label(trading_frame, text="Default Threshold (bp):", style='Custom.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.default_threshold_var = tk.StringVar(value="10.00")
        default_threshold_entry = ttk.Entry(trading_frame, textvariable=self.default_threshold_var, width=15)
        default_threshold_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        save_settings_btn = ttk.Button(trading_frame, text="Save Settings", command=self.save_settings)
        save_settings_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
    def create_future_modules_tab(self):
        """Create a tab for future modules"""
        future_frame = ttk.Frame(self.notebook, style='Custom.TFrame')
        self.notebook.add(future_frame, text="Future Modules")
        
        # Info about future modules
        info_frame = ttk.LabelFrame(future_frame, text="Coming Soon", padding=20)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        info_text = """
        This tab is designed to accommodate future trading modules:
        
        • SmartBalance - Portfolio balancing and rebalancing tools
        • SmartDump - Automated liquidation strategies
        • SmartArbitrage - Cross-exchange arbitrage opportunities
        • SmartAnalytics - Advanced market analysis tools
        • SmartRisk - Risk management and position sizing
        
        Each module will have its own dedicated interface while sharing
        the same underlying trading infrastructure.
        """
        
        info_label = ttk.Label(info_frame, text=info_text, style='Custom.TLabel', justify=tk.LEFT)
        info_label.pack(anchor=tk.W)
        
        # Placeholder for future module selection
        module_frame = ttk.LabelFrame(future_frame, text="Module Selection", padding=20)
        module_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(module_frame, text="Available Modules:", style='Custom.TLabel').pack(anchor=tk.W)
        
        modules = ["SmartBalance (Coming Soon)", "SmartDump (Coming Soon)", "SmartArbitrage (Coming Soon)"]
        for module in modules:
            ttk.Label(module_frame, text=f"• {module}", style='Custom.TLabel').pack(anchor=tk.W, padx=(20, 0))
        
    def create_status_bar(self, parent):
        """Create the status bar"""
        status_frame = ttk.Frame(parent, style='Custom.TFrame')
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        self.status_text = ttk.Label(status_frame, text="Ready", style='Custom.TLabel')
        self.status_text.pack(side=tk.LEFT)
        
        self.time_label = ttk.Label(status_frame, text="", style='Custom.TLabel')
        self.time_label.pack(side=tk.RIGHT)
        
        self.update_time()
        
    def update_time(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
        
    def execute_order(self):
        """Execute a smart market order"""
        if not self.smart_trader:
            messagebox.showerror("Error", "SmartTrader not initialized")
            return
            
        def run_order():
            try:
                pair = self.pair_var.get()
                side = self.side_var.get()
                quantity = float(self.quantity_var.get())
                threshold = float(self.threshold_var.get())
                
                self.log_result(f"Executing {side.upper()} order for {quantity} {pair} (threshold: {threshold}bp)")
                
                result = self.smart_trader._execute_smart_market_order(side, pair, quantity, threshold)
                
                if result:
                    self.log_result(f"Order executed successfully: {result}")
                else:
                    self.log_result("Order execution failed or threshold conditions not met")
                    
            except ValueError as e:
                self.log_result(f"Invalid input: {e}")
            except Exception as e:
                self.log_result(f"Error executing order: {e}")
                
        threading.Thread(target=run_order, daemon=True).start()
        
    def log_result(self, message):
        """Log a result to the results text area"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.results_text.insert(tk.END, formatted_message)
        self.results_text.see(tk.END)
        self.status_text.config(text=message)
        
    def refresh_market_data(self):
        """Refresh market data"""
        if not self.smart_trader:
            return
            
        def update_data():
            try:
                pair = self.market_pair_var.get()
                
                bid = self.smart_trader.get_bid(pair)
                ask = self.smart_trader.get_ask(pair)
                spread = self.smart_trader.get_spread(pair)
                mid_price = self.smart_trader.get_price(pair)
                
                # Update labels
                self.bid_label.config(text=f"${bid:,.2f}" if bid else "Error")
                self.ask_label.config(text=f"${ask:,.2f}" if ask else "Error")
                self.spread_label.config(text=f"{spread:.2f}" if spread else "Error")
                self.mid_label.config(text=f"${mid_price:,.2f}" if mid_price else "Error")
                
                # Update status indicators
                self.bid_status.config(text="✓" if bid else "✗")
                self.ask_status.config(text="✓" if ask else "✗")
                self.spread_status.config(text="✓" if spread else "✗")
                self.mid_status.config(text="✓" if mid_price else "✗")
                
                # Update chart area
                if all([bid, ask, spread, mid_price]):
                    chart_info = f"""
Market Data for {pair}:
{'='*50}
Bid: ${bid:,.2f}
Ask: ${ask:,.2f}
Mid: ${mid_price:,.2f}
Spread: {spread:.2f} bp
Last Updated: {datetime.now().strftime('%H:%M:%S')}
"""
                    self.chart_text.delete(1.0, tk.END)
                    self.chart_text.insert(tk.END, chart_info)
                    
            except Exception as e:
                self.log_result(f"Error refreshing market data: {e}")
                
        threading.Thread(target=update_data, daemon=True).start()
        
    def toggle_auto_refresh(self):
        """Toggle auto-refresh functionality"""
        self.auto_refresh_active = self.auto_refresh_var.get()
        
    def start_auto_refresh(self):
        """Start auto-refresh timer"""
        if self.auto_refresh_active:
            self.refresh_market_data()
        self.root.after(5000, self.start_auto_refresh)
        
    def reconnect_trader(self):
        """Reconnect to the trading system"""
        def reconnect():
            try:
                self.log_result("Reconnecting to trading system...")
                self.initialize_trader()
                self.status_label.config(text=self.connection_status)
                self.log_result("Reconnection completed")
            except Exception as e:
                self.log_result(f"Reconnection failed: {e}")
                
        threading.Thread(target=reconnect, daemon=True).start()
        
    def save_settings(self):
        """Save user settings"""
        settings = {
            "default_pair": self.default_pair_var.get(),
            "default_threshold": self.default_threshold_var.get(),
            "exchange": self.exchange_var.get()
        }
        
        try:
            with open("trading_settings.json", "w") as f:
                json.dump(settings, f, indent=2)
            self.log_result("Settings saved successfully")
            messagebox.showinfo("Success", "Settings saved successfully!")
        except Exception as e:
            self.log_result(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")


def main():
    """Main function to run the GUI"""
    root = tk.Tk()
    app = SmartTraderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()