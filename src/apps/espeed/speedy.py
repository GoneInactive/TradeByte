import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "clients")))
from kraken_python_client import KrakenPythonClient

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
from datetime import datetime, timedelta
import pandas as pd
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
import numpy as np

class TradeByteLiveGraph:
    def __init__(self, parent):
        self.parent = parent
        self.data_points = deque(maxlen=100)  # Store last 100 data points
        self.timestamps = deque(maxlen=100)
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(12, 6), dpi=100, facecolor='#2b2b2b')
        self.ax = self.fig.add_subplot(111, facecolor='#3c3c3c')
        
        # Setup plot styling
        self.setup_plot_style()
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Initialize empty plot
        self.line, = self.ax.plot([], [], '#4a9eff', linewidth=2, label='Response Time')
        self.ax.legend(loc='upper left', facecolor='#2b2b2b', edgecolor='#4a9eff')
        
        # Animation
        self.animation = animation.FuncAnimation(self.fig, self.update_plot, 
                                               interval=1000, blit=False, cache_frame_data=False)
    
    def setup_plot_style(self):
        """Configure plot appearance"""
        self.ax.set_xlabel('Time', color='white', fontsize=10)
        self.ax.set_ylabel('Response Time (ms)', color='white', fontsize=10)
        self.ax.set_title('Real-time Connection Speed Monitor', color='white', fontsize=12, fontweight='bold')
        
        # Grid styling
        self.ax.grid(True, alpha=0.3, color='#666666')
        
        # Axes styling
        self.ax.tick_params(colors='white', labelsize=8)
        self.ax.spines['bottom'].set_color('#666666')
        self.ax.spines['top'].set_color('#666666')
        self.ax.spines['left'].set_color('#666666')
        self.ax.spines['right'].set_color('#666666')
        
        # Set initial limits
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 1000)
    
    def add_data_point(self, response_time):
        """Add new data point to the graph"""
        current_time = datetime.now()
        self.timestamps.append(current_time)
        self.data_points.append(response_time)
    
    def update_plot(self, frame):
        """Update the plot with new data"""
        if len(self.data_points) > 0:
            # Create x-axis based on seconds from start
            if len(self.timestamps) > 1:
                start_time = self.timestamps[0]
                x_data = [(ts - start_time).total_seconds() for ts in self.timestamps]
            else:
                x_data = [0]
            
            y_data = list(self.data_points)
            
            # Update line data
            self.line.set_data(x_data, y_data)
            
            # Auto-scale axes
            if len(x_data) > 1:
                self.ax.set_xlim(min(x_data), max(x_data) + 1)
            
            if len(y_data) > 0:
                y_min = max(0, min(y_data) - 50)
                y_max = max(y_data) + 100
                self.ax.set_ylim(y_min, y_max)
        
        return self.line,
    
    def clear_data(self):
        """Clear all data points"""
        self.data_points.clear()
        self.timestamps.clear()
        self.line.set_data([], [])
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 1000)

class TradeBytePingTestFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()
    
    def create_widgets(self):
        # Test configuration frame
        config_frame = ttk.LabelFrame(self, text="Test Configuration", padding="10")
        config_frame.pack(fill="x", pady=(0, 10))
        
        # Test interval
        interval_frame = ttk.Frame(config_frame)
        interval_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(interval_frame, text="Test Interval (seconds):").pack(side="left")
        self.interval_var = tk.StringVar(value="1.0")
        interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=10)
        interval_entry.pack(side="left", padx=(5, 0))
        
        # Test duration
        duration_frame = ttk.Frame(config_frame)
        duration_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(duration_frame, text="Test Duration (minutes):").pack(side="left")
        self.duration_var = tk.StringVar(value="5")
        duration_entry = ttk.Entry(duration_frame, textvariable=self.duration_var, width=10)
        duration_entry.pack(side="left", padx=(5, 0))
        
        # Test type
        type_frame = ttk.Frame(config_frame)
        type_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(type_frame, text="Test Type:").pack(side="left")
        self.test_type_var = tk.StringVar(value="Bid/Ask")
        type_combo = ttk.Combobox(type_frame, textvariable=self.test_type_var, 
                                 values=["Bid/Ask", "Balance", "Spread", "Order Book"])
        type_combo.pack(side="left", padx=(5, 0))
        type_combo.state(['readonly'])
        
        # Asset selection
        asset_frame = ttk.Frame(config_frame)
        asset_frame.pack(fill="x", pady=(0, 8))
        
        ttk.Label(asset_frame, text="Test Asset:").pack(side="left")
        self.asset_var = tk.StringVar(value="XBTUSD")
        asset_combo = ttk.Combobox(asset_frame, textvariable=self.asset_var,
                                  values=["XBTUSD", "ETHUSD", "ADAUSD", "DOTUSD", "LINKUSD"])
        asset_combo.pack(side="left", padx=(5, 0))

class TradeBytePingTesterGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TradeByte Connection Speed Tester")
        self.root.geometry("1500x950")
        self.root.minsize(1300, 800)
        
        # Initialize Kraken client
        self.kraken_client = KrakenPythonClient(error_message=True)
        
        # Testing state
        self.is_testing = False
        self.test_thread = None
        self.test_results = []
        self.start_time = None
        
        # Enhanced statistics
        self.total_tests = 0
        self.successful_tests = 0
        self.failed_tests = 0
        self.total_response_time = 0
        self.response_times = []  # Store all successful response times
        self.fastest_time = None
        self.slowest_time = None
        self.last_10_times = deque(maxlen=10)  # For recent average
        
        # Setup GUI
        self.setup_styles()
        self.create_widgets()
        
        # Test connection on startup
        self.test_connection()
    
    def setup_styles(self):
        """Configure modern dark theme"""
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
        style.configure('Test.TButton', font=('Arial', 11, 'bold'))
        style.configure('Stop.TButton', font=('Arial', 11, 'bold'))
    
    def create_widgets(self):
        """Create the main GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text="TradeByte Connection Speed Tester", 
                               style='Title.TLabel')
        title_label.pack(side="left")
        
        # Connection status
        self.connection_status = ttk.Label(header_frame, text="● Disconnected", 
                                         style='Status.TLabel')
        self.connection_status.pack(side="right")
        
        # Top panel with configuration and controls
        top_panel = ttk.Frame(main_frame)
        top_panel.pack(fill="x", pady=(0, 20))
        
        # Left side - Configuration
        left_panel = ttk.Frame(top_panel)
        left_panel.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.config_frame = TradeBytePingTestFrame(left_panel)
        self.config_frame.pack(fill="x")
        
        # Right side - Controls and Stats
        right_panel = ttk.Frame(top_panel)
        right_panel.pack(side="right", fill="y")
        
        # Controls
        control_frame = ttk.LabelFrame(right_panel, text="Test Controls", padding="10")
        control_frame.pack(fill="x", pady=(0, 10))
        
        # Test button
        self.test_button = ttk.Button(control_frame, text="Start Test", 
                                     command=self.toggle_test, style='Test.TButton')
        self.test_button.pack(pady=(0, 10), fill="x")
        
        # Clear button
        clear_button = ttk.Button(control_frame, text="Clear Results", 
                                 command=self.clear_results)
        clear_button.pack(pady=(0, 10), fill="x")
        
        # Export button
        export_button = ttk.Button(control_frame, text="Export Results", 
                                  command=self.export_results)
        export_button.pack(fill="x")
        
        # Enhanced Statistics
        stats_frame = ttk.LabelFrame(right_panel, text="Statistics", padding="10")
        stats_frame.pack(fill="both", expand=True)
        
        # Create two columns for statistics
        stats_left = ttk.Frame(stats_frame)
        stats_left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        stats_right = ttk.Frame(stats_frame)
        stats_right.pack(side="right", fill="both", expand=True)
        
        # Left column statistics
        ttk.Label(stats_left, text="Total Tests:", style='Stat.TLabel').pack(anchor="w")
        self.total_tests_label = ttk.Label(stats_left, text="0", style='StatValue.TLabel')
        self.total_tests_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_left, text="Success Rate:", style='Stat.TLabel').pack(anchor="w")
        self.success_rate_label = ttk.Label(stats_left, text="0%", style='StatValue.TLabel')
        self.success_rate_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_left, text="Average Response:", style='Stat.TLabel').pack(anchor="w")
        self.avg_response_label = ttk.Label(stats_left, text="0ms", style='StatValue.TLabel')
        self.avg_response_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_left, text="Current Response:", style='Stat.TLabel').pack(anchor="w")
        self.current_response_label = ttk.Label(stats_left, text="0ms", style='StatValue.TLabel')
        self.current_response_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_left, text="Recent Avg (10):", style='Stat.TLabel').pack(anchor="w")
        self.recent_avg_label = ttk.Label(stats_left, text="0ms", style='StatValueSmall.TLabel')
        self.recent_avg_label.pack(anchor="w", pady=(0, 5))
        
        # Right column statistics
        ttk.Label(stats_right, text="Fastest Time:", style='Stat.TLabel').pack(anchor="w")
        self.fastest_time_label = ttk.Label(stats_right, text="--", style='StatValue.TLabel')
        self.fastest_time_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_right, text="Slowest Time:", style='Stat.TLabel').pack(anchor="w")
        self.slowest_time_label = ttk.Label(stats_right, text="--", style='StatValue.TLabel')
        self.slowest_time_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_right, text="Std Deviation:", style='Stat.TLabel').pack(anchor="w")
        self.std_dev_label = ttk.Label(stats_right, text="0ms", style='StatValue.TLabel')
        self.std_dev_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_right, text="Failed Tests:", style='Stat.TLabel').pack(anchor="w")
        self.failed_tests_label = ttk.Label(stats_right, text="0", style='StatValue.TLabel')
        self.failed_tests_label.pack(anchor="w", pady=(0, 5))
        
        ttk.Label(stats_right, text="Median Time:", style='Stat.TLabel').pack(anchor="w")
        self.median_time_label = ttk.Label(stats_right, text="0ms", style='StatValueSmall.TLabel')
        self.median_time_label.pack(anchor="w", pady=(0, 5))
        
        # Status and progress
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(status_frame, text="Status:", style='Header.TLabel').pack(side="left")
        self.status_label = ttk.Label(status_frame, text="Ready to test", 
                                     style='Status.TLabel')
        self.status_label.pack(side="left", padx=(10, 0))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                          mode='determinate')
        self.progress_bar.pack(fill="x", pady=(0, 10))
        
        # Create notebook for graph and results
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Graph tab
        graph_frame = ttk.Frame(notebook)
        notebook.add(graph_frame, text="Live Graph")
        
        # Create live graph
        self.live_graph = TradeByteLiveGraph(graph_frame)
        
        # Results tab
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="Detailed Results")
        
        # Create results table
        self.create_results_table(results_frame)
    
    def create_results_table(self, parent):
        """Create the results table"""
        # Table frame
        table_frame = ttk.Frame(parent, padding="10")
        table_frame.pack(fill="both", expand=True)
        
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(table_frame)
        tree_frame.pack(fill="both", expand=True)
        
        # Define columns
        columns = ('Timestamp', 'Test Type', 'Asset', 'Response Time', 'Status', 'Details')
        
        self.results_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure column headings and widths
        column_widths = {
            'Timestamp': 120,
            'Test Type': 100,
            'Asset': 80,
            'Response Time': 100,
            'Status': 80,
            'Details': 200
        }
        
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=column_widths[col])
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.results_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.results_tree.xview)
        
        self.results_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack everything
        self.results_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
    
    def test_connection(self):
        """Test initial connection to Kraken API"""
        try:
            if self.kraken_client.test_connection():
                self.connection_status.config(text="● Connected", foreground="#4caf50")
                self.update_status("Connected to Kraken API")
            else:
                self.connection_status.config(text="● Disconnected", foreground="#f44336")
                self.update_status("Failed to connect to Kraken API")
        except Exception as e:
            self.connection_status.config(text="● Error", foreground="#f44336")
            self.update_status(f"Connection error: {str(e)}")
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def perform_speed_test(self, test_type, asset):
        """Perform a single speed test"""
        start_time = time.time()
        
        try:
            if test_type == "Bid/Ask":
                bid = self.kraken_client.get_bid(asset)
                ask = self.kraken_client.get_ask(asset)
                success = bid and ask
                details = f"Bid: {bid}, Ask: {ask}" if success else "Failed to get bid/ask"
                
            elif test_type == "Balance":
                balance = self.kraken_client.get_balance()
                success = balance is not False
                details = "Balance retrieved" if success else "Failed to get balance"
                
            elif test_type == "Spread":
                spread = self.kraken_client.get_spread(asset)
                success = spread is not False
                details = f"Spread: {spread}" if success else "Failed to get spread"
                
            elif test_type == "Order Book":
                orderbook = self.kraken_client.get_orderbook(asset)
                success = orderbook is not False
                details = "Order book retrieved" if success else "Failed to get order book"
            
            else:
                success = False
                details = "Unknown test type"
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            return {
                'timestamp': datetime.now(),
                'test_type': test_type,
                'asset': asset,
                'response_time': response_time,
                'success': success,
                'details': details
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return {
                'timestamp': datetime.now(),
                'test_type': test_type,
                'asset': asset,
                'response_time': response_time,
                'success': False,
                'details': f"Error: {str(e)}"
            }
    
    def update_statistics(self, result):
        """Update statistics display with enhanced metrics"""
        self.total_tests += 1
        
        if result['success']:
            self.successful_tests += 1
            self.total_response_time += result['response_time']
            response_time = result['response_time']
            
            # Store response time for statistical calculations
            self.response_times.append(response_time)
            self.last_10_times.append(response_time)
            
            # Update fastest and slowest times
            if self.fastest_time is None or response_time < self.fastest_time:
                self.fastest_time = response_time
            
            if self.slowest_time is None or response_time > self.slowest_time:
                self.slowest_time = response_time
        else:
            self.failed_tests += 1
        
        # Update all labels
        self.total_tests_label.config(text=str(self.total_tests))
        self.failed_tests_label.config(text=str(self.failed_tests))
        
        # Success rate
        success_rate = (self.successful_tests / self.total_tests) * 100
        self.success_rate_label.config(text=f"{success_rate:.1f}%")
        
        # Average response time
        if self.successful_tests > 0:
            avg_response = self.total_response_time / self.successful_tests
            self.avg_response_label.config(text=f"{avg_response:.1f}ms")
        
        # Current response time
        self.current_response_label.config(text=f"{result['response_time']:.1f}ms")
        
        # Recent average (last 10 tests)
        if len(self.last_10_times) > 0:
            recent_avg = sum(self.last_10_times) / len(self.last_10_times)
            self.recent_avg_label.config(text=f"{recent_avg:.1f}ms")
        
        # Fastest and slowest times
        if self.fastest_time is not None:
            self.fastest_time_label.config(text=f"{self.fastest_time:.1f}ms")
        
        if self.slowest_time is not None:
            self.slowest_time_label.config(text=f"{self.slowest_time:.1f}ms")
        
        # Standard deviation
        if len(self.response_times) > 1:
            std_dev = np.std(self.response_times)
            self.std_dev_label.config(text=f"{std_dev:.1f}ms")
        
        # Median time
        if len(self.response_times) > 0:
            median_time = np.median(self.response_times)
            self.median_time_label.config(text=f"{median_time:.1f}ms")
    
    def add_result_to_table(self, result):
        """Add result to the results table"""
        values = (
            result['timestamp'].strftime('%H:%M:%S'),
            result['test_type'],
            result['asset'],
            f"{result['response_time']:.1f}ms",
            "✓" if result['success'] else "✗",
            result['details']
        )
        
        # Insert at the top of the table
        self.results_tree.insert('', 0, values=values)
        
        # Keep only last 1000 results
        children = self.results_tree.get_children()
        if len(children) > 1000:
            self.results_tree.delete(children[-1])
    
    def test_worker(self):
        """Worker thread for continuous testing"""
        interval = float(self.config_frame.interval_var.get())
        duration_minutes = float(self.config_frame.duration_var.get())
        test_type = self.config_frame.test_type_var.get()
        asset = self.config_frame.asset_var.get()
        
        total_duration = duration_minutes * 60  # Convert to seconds
        total_tests = int(total_duration / interval)
        
        self.start_time = time.time()
        
        for i in range(total_tests):
            if not self.is_testing:
                break
            
            # Perform test
            result = self.perform_speed_test(test_type, asset)
            self.test_results.append(result)
            
            # Update UI
            self.root.after(0, self.update_statistics, result)
            self.root.after(0, self.add_result_to_table, result)
            
            # Update live graph
            if result['success']:
                self.root.after(0, self.live_graph.add_data_point, result['response_time'])
            
            # Update progress
            progress = (i + 1) / total_tests * 100
            self.root.after(0, self.progress_var.set, progress)
            
            # Update status
            elapsed = time.time() - self.start_time
            remaining = total_duration - elapsed
            self.root.after(0, self.update_status, 
                          f"Testing... {i+1}/{total_tests} (Remaining: {remaining:.0f}s)")
            
            # Wait for next test
            time.sleep(interval)
        
        # Test completed
        self.root.after(0, self.test_completed)
    
    def test_completed(self):
        """Handle test completion"""
        self.is_testing = False
        self.test_button.config(text="Start Test")
        self.progress_var.set(0)
        
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        self.update_status(f"Test completed in {elapsed_time:.1f} seconds")
    
    def toggle_test(self):
        """Start or stop testing"""
        if not self.is_testing:
            # Start testing
            self.is_testing = True
            self.test_button.config(text="Stop Test")
            
            # Reset statistics
            self.total_tests = 0
            self.successful_tests = 0
            self.failed_tests = 0
            self.total_response_time = 0
            self.response_times = []
            self.fastest_time = None
            self.slowest_time = None
            self.last_10_times.clear()
            
            # Start test thread
            self.test_thread = threading.Thread(target=self.test_worker)
            self.test_thread.daemon = True
            self.test_thread.start()
        else:
            # Stop testing
            self.is_testing = False
            self.test_button.config(text="Start Test")
            self.update_status("Test stopped by user")
            self.progress_var.set(0)
    
    def clear_results(self):
        """Clear all test results"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        self.test_results = []
        self.live_graph.clear_data()
        
        # Reset all statistics
        self.total_tests = 0
        self.successful_tests = 0
        self.failed_tests = 0
        self.total_response_time = 0
        self.response_times = []
        self.fastest_time = None
        self.slowest_time = None
        self.last_10_times.clear()
        
        # Update all labels
        self.total_tests_label.config(text="0")
        self.failed_tests_label.config(text="0")
        self.success_rate_label.config(text="0%")
        self.avg_response_label.config(text="0ms")
        self.current_response_label.config(text="0ms")
        self.recent_avg_label.config(text="0ms")
        self.fastest_time_label.config(text="--")
        self.slowest_time_label.config(text="--")
        self.std_dev_label.config(text="0ms")
        self.median_time_label.config(text="0ms")
    
    def export_results(self):
        """Export test results to CSV"""
        if not self.test_results:
            messagebox.showwarning("No Results", "No test results to export.")
            return
        
        try:
            # Create DataFrame
            df = pd.DataFrame(self.test_results)
            
            # Format timestamp
            df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate summary statistics
            successful_results = [r for r in self.test_results if r['success']]
            response_times = [r['response_time'] for r in successful_results]
            
            # Create summary statistics
            summary_stats = {
                'Total Tests': len(self.test_results),
                'Successful Tests': len(successful_results),
                'Failed Tests': len(self.test_results) - len(successful_results),
                'Success Rate (%)': (len(successful_results) / len(self.test_results)) * 100 if self.test_results else 0,
                'Average Response Time (ms)': np.mean(response_times) if response_times else 0,
                'Median Response Time (ms)': np.median(response_times) if response_times else 0,
                'Fastest Response Time (ms)': np.min(response_times) if response_times else 0,
                'Slowest Response Time (ms)': np.max(response_times) if response_times else 0,
                'Standard Deviation (ms)': np.std(response_times) if response_times else 0
            }
            
            # Save detailed results to CSV
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_filename = f"connection_speed_test_results_{timestamp}.csv"
            df.to_csv(results_filename, index=False)
            
            # Save summary statistics to CSV
            summary_filename = f"connection_speed_test_summary_{timestamp}.csv"
            summary_df = pd.DataFrame(list(summary_stats.items()), columns=['Metric', 'Value'])
            summary_df.to_csv(summary_filename, index=False)
            
            messagebox.showinfo("Export Successful", 
                              f"Results exported to:\n{results_filename}\n{summary_filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = TradeBytePingTesterGUI()
    app.run()