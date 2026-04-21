from __future__ import annotations

import asyncio
import logging
import struct
from datetime import datetime, timezone
from typing import Callable

import websockets

logger = logging.getLogger(__name__)

class DhanV2WebSocketClient:
    """A client for the Dhan HQ Live Market Feed API v2."""

    BASE_URL = "wss://api-feed.dhan.co"

    def __init__(
        self, 
        client_id: str, 
        access_token: str, 
        instruments: list[tuple[int, int]], # (Segment, SecurityId)
        on_tick: Callable[[int, float, float, datetime], None]
    ):
        self.client_id = client_id
        self.access_token = access_token
        self.instruments = instruments
        self.on_tick = on_tick
        self._running = False

    def get_url(self) -> str:
        """Constructs the v2 handshake URL."""
        return f"{self.BASE_URL}?version=2&token={self.access_token}&clientId={self.client_id}&authType=2"

    async def run(self):
        """Starts the persistent websocket connection."""
        self._running = True
        url = self.get_url()
        
        while self._running:
            try:
                async with websockets.connect(url, ping_interval=10, ping_timeout=10) as ws:
                    logger.info("Dhan v2 WebSocket connected.")
                    
                    # 1. Send subscription packet (format from Dhan docs)
                    # We usually send it once after connection
                    # Format: (FeedRequestCode, InstrumentCount, List of (Segment, SecurityId))
                    # For simplicity, we assume instruments are passed in
                    await self._subscribe(ws)
                    
                    # 2. Receive loop
                    async for message in ws:
                        if isinstance(message, bytes):
                            self._parse_packet(message)
                        else:
                            # Usually Dhan sends Ping-Pong as text or control frames
                            pass
            except Exception as e:
                if self._running:
                    logger.error("Dhan WebSocket connection error: %s. Retrying in 5s...", e)
                    await asyncio.sleep(5)
                else:
                    break

    async def _subscribe(self, ws: websockets.WebSocketClientProtocol):
        """Sends instrument subscription request."""
        # Dhan v2 Subscription Packet is JSON
        import json
        
        segment_map = {
            0: "IDX_I",
            1: "NSE_EQ",
            2: "NSE_FNO",
            3: "NSE_CURRENCY",
            4: "BSE_EQ",
            5: "MCX_COMM",
            7: "BSE_CURRENCY",
            8: "BSE_FNO"
        }
        
        instrument_list = [
            {
                "ExchangeSegment": segment_map.get(seg, "NSE_EQ"),
                "SecurityId": str(sid)
            } for seg, sid in self.instruments
        ]
        
        subscription_message = {
            "RequestCode": 17,  # 17 = Subscribe to Quote Data
            "InstrumentCount": len(self.instruments),
            "InstrumentList": instrument_list
        }
        
        await ws.send(json.dumps(subscription_message))
        logger.info("Subscribed to %d instruments.", len(self.instruments))

    def _parse_packet(self, data: bytes):
        """Decodes the 50-byte binary Quote Packet (Code 4)."""
        if len(data) < 8:
            return

        # Header: Code(1), Len(2), Seg(1), SecurityId(4)
        code, length, segment, sec_id = struct.unpack("<BHBI", data[:8])
        
        if code == 4: # Quote Data
            if len(data) < 50:
                return
            
            # Payload (Offsets 8-49): 
            # 8: LTP(f4), 12: LTT_Qty(i2), 14: LTT(i4), 18: ATP(f4), 22: Volume(i4)
            # 34: Open(f4), 38: Close(f4), 42: High(f4), 46: Low(f4)
            
            # Parsing only what we need for the aggregator: LTP, Volume, and Time
            ltp = struct.unpack("<f", data[8:12])[0]
            ltt = struct.unpack("<I", data[14:18])[0] # Epoch
            volume = struct.unpack("<I", data[22:26])[0]
            
            ts = datetime.fromtimestamp(ltt, tz=timezone.utc)
            self.on_tick(sec_id, ltp, float(volume), ts)
            
        elif code == 3: # Ticker Data (LTP only)
            # Ticker is approx 20 bytes: Header(8) + LTP(4) + Time(4)
            if len(data) >= 16:
                ltp = struct.unpack("<f", data[8:12])[0]
                ltt = struct.unpack("<I", data[12:16])[0]
                ts = datetime.fromtimestamp(ltt, tz=timezone.utc)
                self.on_tick(sec_id, ltp, 0.0, ts) # No volume in ticker mode usually
                
    def stop(self):
        self._running = False
