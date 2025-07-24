import asyncio
import aiohttp
import hashlib
import hmac
import base64
import time
import urllib.parse
import json
import logging
import decimal
from typing import Dict, List, Optional, Any, Union, Callable
from pathlib import Path
import yaml
import websockets

logger = logging.getLogger(__name__)

class KrakenAccount:
    """
    Manages trading operations for a Kraken account using WebSocket v2 API.
    This client is designed for real-time order management and private data streams.
    """
    
    API_URL = "https://api.kraken.com"
    WS_URL_V2 = "wss://ws-auth.kraken.com/v2"
    API_VERSION = "0"
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initializes the KrakenAccount, loading credentials but not connecting."""
        self.api_key = None
        self.api_secret = None
        self._load_credentials(api_key, api_secret)
        
        self._session = None
        self._ws_connection = None
        self._ws_authenticated = False
        self._auth_token = None
        
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._message_handler_task: Optional[asyncio.Task] = None
        self._connection_lock = asyncio.Lock()
        
        # Add handlers for private data streams
        self._private_handlers: Dict[str, List[Callable]] = {}
        self._subscriptions: Dict[str, Dict] = {}

    @classmethod
    async def create(cls, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Factory method to create and connect a KrakenAccount instance using v2."""
        account = cls(api_key, api_secret)
        await account.connect_v2()
        return account

    def _load_credentials(self, api_key: Optional[str], api_secret: Optional[str]):
        """Loads API credentials from a config file or from provided parameters."""
        current_file = Path(__file__)
        config_path = current_file.parent.parent / "config" / "config.yaml"
        config = self._load_config(config_path)
        
        self.api_key = api_key or config.get('kraken', {}).get('api_key')
        self.api_secret = api_secret or config.get('kraken', {}).get('api_secret')
        
        if not self.api_key or not self.api_secret:
            logger.error("API key and secret are required for account operations.")
            raise ValueError("API key and secret not found.")
    
    def _load_config(self, config_path: Path) -> Dict:
        """Loads configuration from a specified YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.warning(f"Configuration file not found at {config_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            return {}
    
    def _get_rest_signature(self, endpoint: str, data: Dict) -> str:
        """Generates the signature for REST API requests."""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = endpoint.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
            
    def _get_ws_auth_token_signature(self, data: Dict) -> str:
        """Generates the signature for the WebSocket authentication token."""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = b'/0/private/GetWebSocketsToken' + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    async def _get_ws_auth_token(self) -> str:
        """Retrieves a WebSocket authentication token from the Kraken REST API."""
        if not self._session:
            self._session = aiohttp.ClientSession()

        data = {'nonce': str(int(1000 * time.time()))}
        headers = {
            'API-Key': self.api_key,
            'API-Sign': self._get_ws_auth_token_signature(data)
        }
        
        url = f"{self.API_URL}/{self.API_VERSION}/private/GetWebSocketsToken"
        
        async with self._session.post(url, headers=headers, data=data) as response:
            result = await response.json()
            
        if result.get('error'):
            raise Exception(f"Failed to get WebSocket token: {result['error']}")
            
        return result['result']['token']

    async def _make_rest_request(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Makes a REST API request to Kraken."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        if data is None:
            data = {}
        
        data['nonce'] = str(int(1000 * time.time()))
        
        headers = {
            'API-Key': self.api_key,
            'API-Sign': self._get_rest_signature(endpoint, data)
        }
        
        url = f"{self.API_URL}{endpoint}"
        
        async with self._session.post(url, headers=headers, data=data) as response:
            result = await response.json()
            
        if result.get('error'):
            raise Exception(f"Kraken API Error: {result['error']}")
            
        return result

    async def connect_v2(self):
        """Establishes and authenticates the WebSocket v2 connection."""
        async with self._connection_lock:
            if self._ws_connection:
                logger.info("WebSocket v2 connection already established.")
                return

            try:
                self._auth_token = await self._get_ws_auth_token()
                
                self._ws_connection = await websockets.connect(
                    self.WS_URL_V2,
                    ping_interval=20,
                    ping_timeout=10
                )
                
                self._ws_authenticated = True
                
                if self._message_handler_task:
                    self._message_handler_task.cancel()
                    
                self._message_handler_task = asyncio.create_task(self._handle_ws_messages_v2())
                logger.info("WebSocket v2 connection established and authenticated.")

            except Exception as e:
                logger.error(f"Failed to establish WebSocket v2 connection: {e}")
                self._ws_authenticated = False
                if self._ws_connection:
                    await self._ws_connection.close()
                raise

    # Legacy method for backward compatibility
    async def connect(self):
        """Legacy connect method - redirects to v2."""
        await self.connect_v2()

    def add_handler(self, event_type: str, handler: Callable):
        """Add a message handler for a specific private data type (e.g., 'ownTrades')."""
        if event_type not in self._private_handlers:
            self._private_handlers[event_type] = []
        self._private_handlers[event_type].append(handler)
        logger.info(f"Added handler for private {event_type}")

    async def _handle_ws_messages_v2(self):
        """Continuously listens for and processes incoming WebSocket v2 messages."""
        try:
            async for message in self._ws_connection:
                try:
                    data = json.loads(message)
                    logger.debug(f"WS v2 Recv: {data}")

                    # Handle method responses (trading requests)
                    if isinstance(data, dict) and "req_id" in data:
                        req_id = data.get("req_id")
                        if req_id in self._pending_requests:
                            future = self._pending_requests.pop(req_id)
                            if not data.get("success", False):
                                error_msg = data.get("error", "Unknown error")
                                future.set_exception(Exception(f"Kraken API Error: {error_msg}"))
                            else:
                                future.set_result(data)
                    
                    # Handle private data streams
                    elif isinstance(data, dict) and "channel" in data and "data" in data:
                        channel_name = data["channel"]
                        if channel_name in self._private_handlers:
                            for handler in self._private_handlers[channel_name]:
                                try:
                                    asyncio.create_task(handler(data))
                                except Exception as e:
                                    logger.error(f"Error in '{channel_name}' handler: {e}")
                    
                    # Handle subscription confirmations
                    elif isinstance(data, dict) and data.get("method") == "subscribe":
                        if data.get("success"):
                            logger.info(f"Successfully subscribed: {data}")
                        else:
                            logger.error(f"Subscription failed: {data.get('error', 'Unknown error')}")
                    
                    # Handle ping messages
                    elif isinstance(data, dict) and data.get("method") == "ping":
                        pong_message = {"method": "pong", "req_id": data.get("req_id")}
                        await self._ws_connection.send(json.dumps(pong_message))

                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode WebSocket message: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket v2 connection closed.")
        except Exception as e:
            logger.error(f"Error in WebSocket v2 message handler: {e}", exc_info=True)
        finally:
            self._ws_authenticated = False
            # Clean up any pending requests that will never resolve
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(Exception("WebSocket connection lost."))
            self._pending_requests.clear()

    def connected(self):
        if not self._ws_authenticated or not self._ws_connection:
            return False
        return True

    async def _send_request_v2(self, payload: Dict, timeout: float = 10.0) -> Dict:
        """Sends a request over WebSocket v2 and waits for a response."""
        if not self._ws_authenticated or not self._ws_connection:
            raise ConnectionError("WebSocket is not connected. Call connect_v2() first.")

        req_id = int(time.time() * 1000)
        payload["req_id"] = req_id
        
        # Add token to params for v2 API
        if "params" not in payload:
            payload["params"] = {}
        payload["params"]["token"] = self._auth_token

        future = asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = future
        
        await self._ws_connection.send(json.dumps(payload))
        logger.debug(f"WS v2 Sent: {payload}")
        
        return await asyncio.wait_for(future, timeout=timeout)

    async def _send_subscription_v2(self, subscription: Dict):
        """Sends a subscription message to the private WebSocket v2."""
        if not self._ws_authenticated or not self._ws_connection:
            raise ConnectionError("WebSocket is not connected. Call connect_v2() first.")
        
        # Add req_id and token
        req_id = int(time.time() * 1000)
        subscription["req_id"] = req_id
        
        if "params" not in subscription:
            subscription["params"] = {}
        subscription["params"]["token"] = self._auth_token
        
        await self._ws_connection.send(json.dumps(subscription))
        logger.debug(f"WS v2 Subscription Sent: {subscription}")

    # --- Private Data Subscriptions (v2 format) ---

    async def subscribe_own_trades(self, 
                                   snapshot: bool = True, 
                                   consolidate_taker: bool = True,
                                   handler: Optional[Callable] = None):
        """
        Subscribe to own trades data stream using v2 format.
        """
        if handler:
            self.add_handler('executions', handler)  # v2 uses 'executions' channel
        
        subscription = {
            "method": "subscribe",
            "params": {
                "channel": "executions",
                "snapshot": snapshot,
                "consolidate_taker": consolidate_taker
            }
        }
        
        await self._send_subscription_v2(subscription)
        self._subscriptions['executions'] = subscription
        logger.info(f"Subscribed to executions (snapshot={snapshot}, consolidate_taker={consolidate_taker})")

    async def subscribe_open_orders(self, handler: Optional[Callable] = None):
        """Subscribe to open orders data stream using v2 format."""
        if handler:
            self.add_handler('orders', handler)  # v2 uses 'orders' channel
        
        subscription = {
            "method": "subscribe",
            "params": {
                "channel": "orders"
            }
        }
        
        await self._send_subscription_v2(subscription)
        self._subscriptions['orders'] = subscription
        logger.info("Subscribed to orders")

    async def unsubscribe_own_trades(self):
        """Unsubscribe from own trades data stream using v2 format."""
        if 'executions' not in self._subscriptions:
            logger.warning("Not subscribed to executions")
            return
        
        unsubscription = {
            "method": "unsubscribe",
            "params": {
                "channel": "executions"
            }
        }
        
        await self._send_subscription_v2(unsubscription)
        self._subscriptions.pop('executions', None)
        logger.info("Unsubscribed from executions")

    async def unsubscribe_open_orders(self):
        """Unsubscribe from open orders data stream using v2 format."""
        if 'orders' not in self._subscriptions:
            logger.warning("Not subscribed to orders")
            return
        
        unsubscription = {
            "method": "unsubscribe",
            "params": {
                "channel": "orders"
            }
        }
        
        await self._send_subscription_v2(unsubscription)
        self._subscriptions.pop('orders', None)
        logger.info("Unsubscribed from orders")

    # --- Account Information Methods ---

    async def get_balance(self) -> Dict[str, str]:
        """
        Retrieves account balance via REST API.
        
        Returns:
            Dict mapping currency codes to balance amounts as strings.
            Example: {'ZUSD': '1000.0000', 'XXBT': '0.50000000'}
        """
        result = await self._make_rest_request(f"/{self.API_VERSION}/private/Balance")
        return result['result']

    # --- Trading Methods (v2 API) ---

    async def add_order_v2(self, symbol: str, side: str, order_type: str, 
                  order_qty: Union[str, float, decimal.Decimal], 
                  limit_price: Optional[Union[str, float, decimal.Decimal]] = None,
                  display_qty: Optional[Union[str, float, decimal.Decimal]] = None, 
                  validate: bool = False, 
                  **kwargs) -> Dict:
        """
        Places orders using the v2 API format.
        Supports all order types including iceberg orders.
        """
        def format_number(value):
            """Ensure numeric values are properly formatted as floats for v2 API"""
            if value is None:
                return None
            if isinstance(value, (str, int, float, decimal.Decimal)):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid numeric value: {value}")
            return value

        payload = {
            "method": "add_order",
            "params": {
                "order_type": order_type,
                "side": side,
                "symbol": symbol,
                "order_qty": format_number(order_qty),
                "validate": validate
            }
        }
        
        if limit_price is not None:
            payload["params"]["limit_price"] = format_number(limit_price)
        
        if display_qty is not None:
            if order_type == "iceberg":
                # Validate minimum display quantity
                try:
                    display_val = float(display_qty)
                    order_val = float(order_qty)
                    min_display = order_val / 15.0
                    if display_val < min_display:
                        raise ValueError(
                            f"Display quantity must be at least {min_display} "
                            f"(1/15 of order quantity)"
                        )
                except (ValueError, TypeError) as e:
                    raise ValueError("Invalid numeric values provided") from e
            payload["params"]["display_qty"] = format_number(display_qty)
        
        payload["params"].update(kwargs)
        return await self._send_request_v2(payload)

    async def amend_order_v2(self, order_id: Optional[str] = None, 
                        cl_ord_id: Optional[str] = None,
                        order_qty: Optional[Union[str, float, decimal.Decimal]] = None,
                        limit_price: Optional[Union[str, float, decimal.Decimal]] = None,
                        display_qty: Optional[Union[str, float, decimal.Decimal]] = None,
                        **kwargs) -> Dict:
        """
        Amends an order using v2 API format.
        """
        if not order_id and not cl_ord_id:
            raise ValueError("Either order_id or cl_ord_id must be provided")
        
        def format_number(value):
            """Ensure numeric values are properly formatted as floats for v2 API"""
            if value is None:
                return None
            if isinstance(value, (str, int, float, decimal.Decimal)):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid numeric value: {value}")
            return value
        
        payload = {
            "method": "amend_order", 
            "params": {}
        }
        
        # Set order identifier
        if order_id:
            payload["params"]["order_id"] = order_id
        if cl_ord_id:
            payload["params"]["cl_ord_id"] = cl_ord_id
        
        # Add parameters to modify
        if order_qty is not None:
            payload["params"]["order_qty"] = format_number(order_qty)
        if limit_price is not None:
            payload["params"]["limit_price"] = format_number(limit_price)
        if display_qty is not None:
            payload["params"]["display_qty"] = format_number(display_qty)
        
        # Validate display_qty if both order_qty and display_qty are provided
        if order_qty is not None and display_qty is not None:
            display_qty_float = float(display_qty)
            order_qty_float = float(order_qty)
            min_display_qty = order_qty_float / 15.0
            if display_qty_float < min_display_qty:
                raise ValueError(f"Display quantity {display_qty} must be at least {min_display_qty:.8f} (1/15 of order quantity)")
        
        # Add any additional parameters
        payload["params"].update(kwargs)
        return await self._send_request_v2(payload)

    async def cancel_order_v2(self, order_id: Optional[str] = None, 
                             cl_ord_id: Optional[str] = None) -> Dict:
        """Cancel an order using v2 API format."""
        if not order_id and not cl_ord_id:
            raise ValueError("Either order_id or cl_ord_id must be provided")
        
        payload = {
            "method": "cancel_order",
            "params": {}
        }
        
        if order_id:
            payload["params"]["order_id"] = order_id
        if cl_ord_id:
            payload["params"]["cl_ord_id"] = cl_ord_id
        
        return await self._send_request_v2(payload)

    async def cancel_all_orders_v2(self) -> Dict:
        """Cancel all orders using v2 API format."""
        payload = {
            "method": "cancel_all_orders",
            "params": {}
        }
        return await self._send_request_v2(payload)

    async def cancel_all_orders_after_v2(self, timeout: int) -> Dict:
        """Cancel all orders after a timeout using v2 API format."""
        payload = {
            "method": "cancel_all_orders_after",
            "params": {
                "timeout": timeout
            }
        }
        return await self._send_request_v2(payload)

    # --- Legacy v1 methods for backward compatibility ---

    async def add_order(self, pair: str, type: str, ordertype: str, volume: str,
                       price: Optional[str] = None, validate: bool = False, **kwargs) -> Dict:
        """
        Legacy method for backward compatibility.
        Converts v1 parameters to v2 format internally.
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

    async def edit_order(self, txid: str, volume: Optional[str] = None,
                        limit_price: Optional[str] = None, **kwargs) -> Dict:
        """Legacy method - edits an existing order."""
        return await self.amend_order_v2(
            order_id=txid,
            order_qty=volume,
            limit_price=limit_price,
            **kwargs
        )

    # In your KrakenPythonClient class
    async def cancel_order(self, order_id):
        """
        Async version of cancel_order that makes the HTTP request
        """
        try:
            # Use aiohttp or similar async HTTP client here
            async with self.session.post(
                f"{self.base_url}/cancel_order",
                json={"txid": order_id},
                headers=self._get_auth_headers()
            ) as response:
                return await response.json()
        except Exception as e:
            print(f"Error canceling order {order_id}: {e}")
            return {"status": "error", "errorMessage": str(e)}

    async def cancel_all_orders(self) -> Dict:
        """Legacy method - cancels all open orders."""
        return await self.cancel_all_orders_v2()

    # --- Iceberg Order Convenience Methods ---

    async def add_iceberg_order(self, symbol: str, side: str, order_qty: str, 
                               limit_price: str, display_qty: str, 
                               validate: bool = False, **kwargs) -> Dict:
        """Convenience method for placing iceberg orders."""
        return await self.add_order_v2(
            symbol=symbol,
            side=side,
            order_type="iceberg",
            order_qty=order_qty,
            limit_price=limit_price,
            display_qty=display_qty,
            validate=validate,
            **kwargs
        )

    async def amend_iceberg_order(self, order_id: Optional[str] = None, 
                                 cl_ord_id: Optional[str] = None,
                                 order_qty: Optional[str] = None,
                                 limit_price: Optional[str] = None,
                                 display_qty: Optional[str] = None,
                                 **kwargs) -> Dict:
        """Convenience method for amending iceberg orders."""
        return await self.amend_order_v2(
            order_id=order_id,
            cl_ord_id=cl_ord_id,
            order_qty=order_qty,
            limit_price=limit_price,
            display_qty=display_qty,
            **kwargs
        )

    # --- Utility Methods ---

    async def get_open_orders(self) -> Dict:
        """Get open orders via REST API."""
        result = await self._make_rest_request(f"/{self.API_VERSION}/private/OpenOrders")
        return result['result']

    async def get_closed_orders(self) -> Dict:
        """Get closed orders via REST API."""
        result = await self._make_rest_request(f"/{self.API_VERSION}/private/ClosedOrders")
        return result['result']

    async def get_trades_history(self) -> Dict:
        """Get trades history via REST API."""
        result = await self._make_rest_request(f"/{self.API_VERSION}/private/TradesHistory")
        return result['result']

    async def query_orders_info(self, txid: Union[str, List[str]]) -> Dict:
        """Query orders info via REST API."""
        if isinstance(txid, list):
            txid = ','.join(txid)
        
        data = {'txid': txid}
        result = await self._make_rest_request(f"/{self.API_VERSION}/private/QueryOrders", data)
        return result['result']

    async def query_trades_info(self, txid: Union[str, List[str]]) -> Dict:
        """Query trades info via REST API."""
        if isinstance(txid, list):
            txid = ','.join(txid)
        
        data = {'txid': txid}
        result = await self._make_rest_request(f"/{self.API_VERSION}/private/QueryTrades", data)
        return result['result']

    async def close(self):
        """Closes the WebSocket connection and cleans up resources."""
        if self._message_handler_task:
            self._message_handler_task.cancel()
            try:
                await self._message_handler_task
            except asyncio.CancelledError:
                pass
        
        if self._ws_connection:
            await self._ws_connection.close()
            logger.info("WebSocket v2 connection closed.")
        
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        await self.connect_v2()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()