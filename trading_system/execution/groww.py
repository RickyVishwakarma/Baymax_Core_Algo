from __future__ import annotations

import logging
import requests
import uuid

from trading_system.models import Fill, MarketBar, Order, Side
from trading_system.execution.base import ExecutionHandler

logger = logging.getLogger(__name__)

class GrowwExecutionHandler(ExecutionHandler):
    """
    Live execution handler for integrating with Groww's APIs.
    """
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        
        self.base_url = "https://api.groww.in/v1/order/create"
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-API-VERSION": "1.0",
            "User-Agent": "AutomatedTradingPlatform/1.0"
        })

    def execute(self, order: Order, bar: MarketBar) -> Fill:
        """
        Submits a LIVE market order to Groww.
        """
        side_str = "BUY" if order.side == Side.BUY else "SELL"
        
        payload = {
            "validity": "DAY",
            "exchange": "NSE",
            "transaction_type": side_str,
            "order_type": "MARKET",
            "price": 0,
            "product": "CNC",
            "quantity": int(order.size),
            "segment": "CASH",
            "trading_symbol": order.symbol
        }
        
        logger.warning(f"GROWW LIVE EXECUTION: Attempting {side_str} {order.size} units of {order.symbol}")
        
        try:
            response = self.session.post(self.base_url, json=payload, timeout=5)
            
            if response.status_code not in (200, 201):
                logger.error(f"Groww execution failed! Status: {response.status_code}, Body: {response.text}")
            else:
                logger.info(f"Groww order placed successfully: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Network error while reaching Groww API: {e}")
            
        # Mocking the fill locally as market order since we aren't hooking into an order status stream.
        return Fill(
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            fill_price=bar.close, 
            fee_paid=0.0
        )
