from __future__ import annotations

import logging
import time
import uuid
import requests
from typing import Any

from trading_system.models import Fill, MarketBar, Order, Side
from trading_system.execution.base import ExecutionHandler
from trading_system.data.dhan_manager import DhanInstrumentManager

logger = logging.getLogger(__name__)

class DhanExecutionHandler(ExecutionHandler):
    """
    Live execution handler for Dhan HQ API v2.
    Places MARKET orders and polls for TRADE confirmation.
    """

    BASE_URL = "https://api.dhan.co/v2"

    def __init__(
        self, 
        client_id: str, 
        access_token: str, 
        instrument_manager: DhanInstrumentManager,
        product_type: str = "INTRADAY", # MIS/INTRADAY, CNC/DELIVERY
        exchange: str = "NSE"
    ):
        self.client_id = client_id
        self.access_token = access_token
        self.instrument_manager = instrument_manager
        self.product_type = product_type
        self.exchange = exchange
        self.headers = {
            "access-token": self.access_token,
            "Content-Type": "application/json"
        }

    def execute(self, order: Order, bar: MarketBar) -> Fill:
        """
        Executes an order on Dhan and waits for it to be TRADED.
        """
        # 1. Map symbol to SecurityId and Segment
        metadata = self.instrument_manager.get_instrument_metadata(self.exchange, order.symbol)
        sec_id = metadata["security_id"]
        segment = metadata["segment"]

        # 2. Prepare Order Payload
        correlation_id = str(uuid.uuid4())
        payload = {
            "dhanClientId": self.client_id,
            "correlationId": correlation_id,
            "transactionType": "BUY" if order.side == Side.BUY else "SELL",
            "exchangeSegment": segment,
            "productType": self.product_type,
            "orderType": "MARKET",
            "validity": "DAY",
            "securityId": sec_id,
            "quantity": int(abs(order.size)),
            "price": 0.0 # 0.0 for MARKET orders
        }

        logger.info("Placing %s order for %s on Dhan. Qty: %d", order.side.value, order.symbol, payload["quantity"])
        
        try:
            resp = requests.post(f"{self.BASE_URL}/orders", json=payload, headers=self.headers, timeout=10)
            resp.raise_for_status()
            order_data = resp.json()
            order_id = order_data.get("orderId")
            
            if not order_id:
                raise RuntimeError(f"Dhan order placement failed: {order_data}")

            # 3. Poll for Status
            return self._poll_for_fill(order_id, order)

        except Exception as e:
            logger.error("Dhan execution error for %s: %s", order.symbol, e)
            # In a live system, we might want to return None or a 'FAILED' fill, 
            # but here we'll raise so the bot knows something is wrong.
            raise

    def _poll_for_fill(self, order_id: str, order: Order, timeout_sec: int = 15) -> Fill:
        """
        Polls the Dhan order status until it's TRADED or timed out.
        """
        start_time = time.time()
        while (time.time() - start_time) < timeout_sec:
            try:
                resp = requests.get(f"{self.BASE_URL}/orders/{order_id}", headers=self.headers, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                
                status = data.get("orderStatus")
                if status == "TRADED":
                    # Fully filled
                    fill_price = float(data.get("avgPrice", 0.0))
                    return Fill(
                        symbol=order.symbol,
                        side=order.side,
                        size=order.size,
                        fill_price=fill_price,
                        fee_paid=0.0 # Dhan fees are separate, we could estimate bps here
                    )
                elif status in ["REJECTED", "CANCELLED"]:
                    raise RuntimeError(f"Dhan order {order_id} {status}: {data.get('omsErrorMsg')}")
                
                logger.info("Order %s status: %s. Waiting...", order_id, status)
                time.sleep(1) # Poll interval
            except Exception as e:
                logger.warning("Polling error for order %s: %s", order_id, e)
                time.sleep(1)

        raise TimeoutError(f"Dhan order {order_id} did not fill within {timeout_sec}s")
