import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "clients")))
from kraken_python_client import KrakenPythonClient

class Metrics:
    def __init__(self):
        self.client = KrakenPythonClient()
    
    def portfolio_value(self, base_currency='USD'):
        """
        Returns the portfolio value based on mid point value
       
        Sample Balance:
        {'SCRT': 0.0, 'GLD.EQ': 0.032584115, 'SOL': 0.0, 'XXDG': 6.17314041,
        'USDG.F': 1.51513081, 'PEPE': 85714.29, 'XTZ': 0.0, 'USDS': 0.0,
        'XTZ.F': 0.00210322, 'ZEUR': 27.4129, 'TOKEN': 0.0, 'USDC': 0.0,
        'EURT': 0.0, 'SPY.EQ': 0.0, 'ZUSD': 245.1351, 'XETH': 0.0,
        'EURR': 24.17027, 'EURQ': 237.31542, 'TAO.F': 3.53e-05, 'USDG': 0.0,
        'SOL.F': 0.0020019058, 'USDT': 25.0, 'EWT': 0.0, 'USDQ': 108.32817,
        'ETH.F': 6e-08, 'TAO': 0.0, 'TUSD': 0.0, 'XXBT': 9.69e-08}
        """
        value = 0.0
        balances = self.client.get_balance()
        
        for currency, amount in balances.items():
            # Skip zero or negligible balances
            if amount < 0.0001:
                continue
                
            # Handle base currency (e.g., ZUSD for USD)
            if currency == 'Z' + base_currency or currency == base_currency:
                value += amount
            else:
                # Skip derivatives and futures for now (contain ".")
                if "." in currency:
                    continue
                    
                # Try different pair formats
                price = self._get_currency_price(currency, base_currency)
                if price:
                    value += price * amount
                   
        print(f"Total portfolio value: {value:.2f} {base_currency}")
        return value
    
    def _get_currency_price(self, currency, base_currency):
        """
        Get the mid-point price for a currency pair, trying multiple formats.
        """
        # Common pair formats to try
        pair_variations = [
            currency + base_currency,
            currency + '/' + base_currency,
            currency + 'Z' + base_currency,
            'X' + currency + 'Z' + base_currency,
            base_currency + currency,
            'Z' + base_currency + 'X' + currency,
            'Z' + base_currency + currency
        ]
        
        for pair in pair_variations:
            try:
                ask = self.client.get_ask(pair)
                bid = self.client.get_bid(pair)
                
                if ask and bid and ask > 0 and bid > 0:
                    # Check if this is an inverse pair
                    if pair.startswith(base_currency) or pair.startswith('Z' + base_currency):
                        # Inverse pair - we need to invert the price
                        price = 2 / (ask + bid)
                    else:
                        # Direct pair
                        price = (ask + bid) / 2
                    
                    return price
                    
            except Exception as e:
                # Continue trying other pair formats
                continue
        
        print(f"Warning: Could not find price for {currency}")
        return None
    
    def get_detailed_portfolio(self, base_currency='USD'):
        """
        Returns detailed portfolio breakdown with individual asset values.
        """
        portfolio = {
            'holdings': {},
            'total_value': 0.0,
            'base_currency': base_currency,
            'errors': []
        }
        
        balances = self.client.get_balance()
        
        for currency, amount in balances.items():
            # Skip zero or negligible balances
            if amount < 0.0001:
                continue
                
            asset_info = {
                'balance': amount,
                'value_in_base': 0.0,
                'price': 0.0
            }
            
            # Handle base currency
            if currency == 'Z' + base_currency or currency == base_currency:
                asset_info['value_in_base'] = amount
                asset_info['price'] = 1.0
            else:
                # Skip derivatives and futures for detailed view
                if "." in currency:
                    portfolio['errors'].append(f"Skipped derivative asset: {currency}")
                    continue
                    
                price = self._get_currency_price(currency, base_currency)
                if price:
                    asset_info['price'] = price
                    asset_info['value_in_base'] = amount * price
                else:
                    portfolio['errors'].append(f"Could not find price for {currency}")
            
            portfolio['holdings'][currency] = asset_info
            portfolio['total_value'] += asset_info['value_in_base']
        
        return portfolio
    
    def print_portfolio_summary(self, base_currency='USD'):
        """
        Print a formatted summary of the portfolio.
        """
        portfolio = self.get_detailed_portfolio(base_currency)
        
        print(f"\n=== Portfolio Summary ({base_currency}) ===")
        print(f"Total Portfolio Value: {portfolio['total_value']:.2f} {base_currency}")
        print("\nHoldings:")
        print("-" * 70)
        
        # Sort holdings by value (descending)
        sorted_holdings = sorted(
            portfolio['holdings'].items(), 
            key=lambda x: x[1]['value_in_base'], 
            reverse=True
        )
        
        for asset, info in sorted_holdings:
            percentage = (info['value_in_base'] / portfolio['total_value'] * 100) if portfolio['total_value'] > 0 else 0
            print(f"{asset:>10}: {info['balance']:>15.6f} @ {info['price']:>12.4f} = {info['value_in_base']:>12.2f} {base_currency} ({percentage:>5.1f}%)")
        
        if portfolio['errors']:
            print(f"\nWarnings:")
            for error in portfolio['errors']:
                print(f"  - {error}")
        
        return portfolio