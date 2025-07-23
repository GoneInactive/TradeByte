import asyncio
import json
import websockets
import logging
from typing import Dict, List, Callable, Optional, Any
from pathlib import Path
import yaml
import hashlib
import hmac
import base64
import time
import urllib.parse

from account import KrakenAccount
from markets import KrakenMarkets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KrakenWebSocket:
    """
    Kraken WebSocket client for real-time data streaming and trading.
    Updated to use v2 API endpoints consistently.
    """
    
    # Updated to v2 endpoints
    WS_PUBLIC_URL = "wss://ws.kraken.com/v2"
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.public_ws = None
        self.is_connected = False
        
        self.handlers: Dict[str, List[Callable]] = {}
        self.subscriptions: Dict[str, Dict] = {}
        
        # Initialize components - account will manage its own v2 connection
        self.account = KrakenAccount(api_key, api_secret)
        self.markets = KrakenMarkets()
        
        self._running = False

        
    async def connect(self, private: bool = False):
        """
        Connects to the necessary WebSocket endpoints.
        - Public connection for market data (v2).
        - Private connection is handled by the account object (v2).
        """
        if not self.public_ws:
            self.public_ws = await websockets.connect(self.WS_PUBLIC_URL)
            self.is_connected = True
            logger.info("Connected to Kraken public WebSocket v2 for market data.")

        if private:
            # The account object manages its own v2 connection
            await self.account.connect_v2()
    
    def add_handler(self, event_type: str, handler: Callable):
        """Add a message handler for a specific data type (e.g., 'book', 'trade')."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Added handler for {event_type}")

    # --- Public Market Data Subscriptions (v2 format) ---

    async def subscribe_book(self, symbols: List[str], depth: int = 10, handler: Optional[Callable] = None):
        """Subscribe to order book data using v2 format."""
        if handler:
            self.add_handler('book', handler)
        
        # v2 subscription format
        subscription = {
            "method": "subscribe",
            "params": {
                "channel": "book",
                "symbol": symbols,
                "depth": depth
            }
        }
        
        await self._send_public_subscription(subscription)
        self.subscriptions['book'] = subscription
        logger.info(f"Subscribed to order book for symbols: {symbols}, depth: {depth}")

    async def subscribe_trades(self, symbols: List[str], handler: Optional[Callable] = None):
        """Subscribe to trade data using v2 format."""
        if handler:
            self.add_handler('trade', handler)
        
        # v2 subscription format
        subscription = {
            "method": "subscribe", 
            "params": {
                "channel": "trade",
                "symbol": symbols
            }
        }
        
        await self._send_public_subscription(subscription)
        self.subscriptions['trade'] = subscription
        logger.info(f"Subscribed to trades for symbols: {symbols}")

    async def subscribe_ticker(self, symbols: List[str], handler: Optional[Callable] = None):
        """Subscribe to ticker data using v2 format."""
        if handler:
            self.add_handler('ticker', handler)
        
        subscription = {
            "method": "subscribe",
            "params": {
                "channel": "ticker", 
                "symbol": symbols
            }
        }
        
        await self._send_public_subscription(subscription)
        self.subscriptions['ticker'] = subscription
        logger.info(f"Subscribed to ticker for symbols: {symbols}")

    async def subscribe_ohlc(self, symbols: List[str], interval: int = 1, handler: Optional[Callable] = None):
        """Subscribe to OHLC data using v2 format."""
        if handler:
            self.add_handler('ohlc', handler)
        
        subscription = {
            "method": "subscribe",
            "params": {
                "channel": "ohlc",
                "symbol": symbols,
                "interval": interval
            }
        }
        
        await self._send_public_subscription(subscription)
        self.subscriptions['ohlc'] = subscription
        logger.info(f"Subscribed to OHLC for symbols: {symbols}, interval: {interval}")

    # --- Private Data Subscriptions (delegated to account v2) ---

    async def subscribe_own_trades(self, 
                                   snapshot: bool = True, 
                                   consolidate_taker: bool = True,
                                   handler: Optional[Callable] = None):
        """
        Subscribe to own trades data stream using v2 format.
        """
        # Ensure the account is connected to v2
        if not self.account.connected():
            await self.account.connect_v2()
        
        await self.account.subscribe_own_trades(
            snapshot=snapshot,
            consolidate_taker=consolidate_taker,
            handler=handler
        )

    async def subscribe_open_orders(self, handler: Optional[Callable] = None):
        """Subscribe to open orders data stream using v2 format."""
        if not self.account.connected():
            await self.account.connect_v2()
        
        await self.account.subscribe_open_orders(handler=handler)

    async def unsubscribe_own_trades(self):
        """Unsubscribe from own trades data stream."""
        await self.account.unsubscribe_own_trades()

    async def unsubscribe_open_orders(self):
        """Unsubscribe from open orders data stream."""
        await self.account.unsubscribe_open_orders()

    # --- Enhanced Trading Methods (v2 API) ---

    async def add_order_v2(self, symbol: str, side: str, order_type: str, 
                          order_qty: str, limit_price: Optional[str] = None,
                          display_qty: Optional[str] = None, validate: bool = False, 
                          **kwargs) -> Dict:
        """
        Places orders using the v2 API format.
        Supports all order types including iceberg orders.
        """
        if not self.account.connected():
            await self.account.connect_v2()
            
        return await self.account.add_order_v2(
            symbol=symbol,
            side=side,
            order_type=order_type,
            order_qty=order_qty,
            limit_price=limit_price,
            display_qty=display_qty,
            validate=validate,
            **kwargs
        )

    async def amend_order_v2(self, order_id: Optional[str] = None, 
                            cl_ord_id: Optional[str] = None,
                            order_qty: Optional[str] = None,
                            limit_price: Optional[str] = None,
                            display_qty: Optional[str] = None,
                            **kwargs) -> Dict:
        """
        Amends an order using v2 API format.
        """
        if not self.account.connected():
            await self.account.connect_v2()
        
        return await self.account.amend_order_v2(
            order_id=order_id,
            cl_ord_id=cl_ord_id,
            order_qty=order_qty,
            limit_price=limit_price,
            display_qty=display_qty,
            **kwargs
        )

    async def cancel_order_v2(self, order_id: Optional[str] = None, 
                             cl_ord_id: Optional[str] = None) -> Dict:
        """Cancel an order using v2 API format."""
        if not self.account.connected():
            await self.account.connect_v2()
        
        return await self.account.cancel_order_v2(order_id=order_id, cl_ord_id=cl_ord_id)

    async def cancel_all_orders_v2(self) -> Dict:
        """Cancel all orders using v2 API format."""
        if not self.account.connected():
            await self.account.connect_v2()
        
        return await self.account.cancel_all_orders_v2()

    # --- Legacy v1 methods for backward compatibility ---

    async def add_order(self, pair: str, type: str, ordertype: str, volume: str,
                       price: Optional[str] = None, validate: bool = False, **kwargs) -> Dict:
        """
        Legacy method for backward compatibility.
        Internally converts to v2 format.
        """
        # Convert v1 parameters to v2 format
        symbol = pair  # May need symbol mapping
        side = type  # "buy" or "sell"
        order_type = ordertype  # "limit", "market", etc.
        order_qty = volume
        limit_price = price
        
        return await self.add_order_v2(
            symbol=symbol,
            side=side,
            order_type=order_type,
            order_qty=order_qty,
            limit_price=limit_price,
            validate=validate,
            **kwargs
        )

    async def cancel_order(self, txid):
        """Cancel an order (legacy v1 method)."""
        return await self.cancel_order_v2(order_id=txid)

    async def cancel_all_orders(self):
        """Cancel all orders (legacy v1 method)."""
        return await self.cancel_all_orders_v2()

    # --- Account Information Methods ---

    async def get_balance(self) -> Dict[str, str]:
        """Get account balance via the account object."""
        if not self.account.connected():
            await self.account.connect_v2()
        
        return await self.account.get_balance()

    async def _send_public_subscription(self, subscription: Dict):
        """Sends a subscription message to the public WebSocket v2."""
        if not self.is_connected or not self.public_ws:
            await self.connect()
        
        # Add req_id for v2 format
        req_id = int(time.time() * 1000)
        subscription["req_id"] = req_id
        
        await self.public_ws.send(json.dumps(subscription))

    async def _handle_public_message(self, message: str):
        """Handles incoming public market data messages in v2 format."""
        try:
            data = json.loads(message)
            
            # Handle subscription confirmations and errors
            if isinstance(data, dict) and 'method' in data:
                if data['method'] == 'subscribe':
                    if data.get('success'):
                        logger.info(f"Successfully subscribed: {data}")
                    else:
                        logger.error(f"Subscription failed: {data.get('error', 'Unknown error')}")
                elif data['method'] == 'ping':
                    # Respond to ping
                    pong = {"method": "pong", "req_id": data.get("req_id")}
                    await self.public_ws.send(json.dumps(pong))
                return

            # Handle data messages - v2 format is different
            if isinstance(data, dict) and 'channel' in data and 'data' in data:
                channel_name = data['channel']
                
                if channel_name in self.handlers:
                    for handler in self.handlers[channel_name]:
                        try:
                            asyncio.create_task(handler(data))
                        except Exception as e:
                            logger.error(f"Error in '{channel_name}' handler: {e}")
            else:
                logger.debug(f"Received message with unexpected format: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling public message: {e}")

    async def run(self):
        """Starts the client and keeps it running."""
        if not self.public_ws:
            raise ConnectionError("Not connected. Call connect() before running.")
            
        self._running = True
        logger.info("KrakenWebSocket v2 client is running...")
        
        try:
            while self._running:
                message = await self.public_ws.recv()
                await self._handle_public_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Public WebSocket connection lost. Exiting run loop.")
        except Exception as e:
            logger.error(f"An error occurred in the run loop: {e}")
        finally:
            self._running = False

    async def close(self):
        """Closes all connections."""
        self._running = False
        
        # Close public connection
        if self.public_ws:
            await self.public_ws.close()
            logger.info("Public WebSocket connection closed.")
            
        # Close private connection via the account object
        await self.account.close()