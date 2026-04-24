"""
Broker integration layer.
For now we intentionally support one broker path: Upstox.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BrokerStatus:
    broker: str
    configured: bool
    live_ready: bool
    paper_ready: bool
    message: str


@dataclass
class OrderRequest:
    symbol: str
    quantity: int
    instrument_token: Optional[str] = None
    transaction_type: str = "BUY"
    order_type: str = "MARKET"
    product: str = "I"
    validity: str = "DAY"
    price: float = 0.0
    trigger_price: float = 0.0
    is_amo: bool = False
    tag: Optional[str] = None


@dataclass
class OrderResponse:
    accepted: bool
    status: str
    broker_order_id: Optional[str]
    message: str
    payload: Optional[dict] = None


class BrokerAdapter(ABC):
    @abstractmethod
    def get_status(self) -> BrokerStatus:
        raise NotImplementedError

    @abstractmethod
    def place_intraday_order(self, request: OrderRequest) -> OrderResponse:
        raise NotImplementedError


class UpstoxBrokerAdapter(BrokerAdapter):
    def __init__(self) -> None:
        self.base_url = settings.UPSTOX_API_BASE_URL.rstrip("/")
        self.access_token = settings.UPSTOX_ACCESS_TOKEN.strip()

    def get_status(self) -> BrokerStatus:
        configured = bool(self.access_token)
        if not configured:
            return BrokerStatus(
                broker="upstox",
                configured=False,
                live_ready=False,
                paper_ready=True,
                message="Upstox access token is missing. Paper mode is available; live mode remains blocked.",
            )

        if not settings.ALLOW_LIVE_TRADING:
            return BrokerStatus(
                broker="upstox",
                configured=True,
                live_ready=False,
                paper_ready=True,
                message="Broker token is configured, but ALLOW_LIVE_TRADING is False so live orders are still blocked.",
            )

        return BrokerStatus(
            broker="upstox",
            configured=True,
            live_ready=True,
            paper_ready=True,
            message="Broker credentials are present. Provide instrument tokens per order before sending live trades.",
        )

    def place_intraday_order(self, request: OrderRequest) -> OrderResponse:
        status = self.get_status()
        if not status.configured:
            return OrderResponse(
                accepted=False,
                status="rejected",
                broker_order_id=None,
                message=status.message,
            )

        if not settings.ALLOW_LIVE_TRADING:
            return OrderResponse(
                accepted=False,
                status="blocked",
                broker_order_id=None,
                message="Live trading is disabled in configuration.",
            )

        if not request.instrument_token:
            return OrderResponse(
                accepted=False,
                status="rejected",
                broker_order_id=None,
                message="Upstox live orders require instrument_token for each symbol.",
            )

        payload = {
            "quantity": request.quantity,
            "product": request.product,
            "validity": request.validity,
            "price": request.price,
            "tag": request.tag or f"stock-analyser-{request.symbol.lower()}",
            "instrument_token": request.instrument_token,
            "order_type": request.order_type,
            "transaction_type": request.transaction_type,
            "disclosed_quantity": 0,
            "trigger_price": request.trigger_price,
            "is_amo": request.is_amo,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

        try:
            response = httpx.post(
                f"{self.base_url}/order/place",
                json=payload,
                headers=headers,
                timeout=20.0,
            )
            response.raise_for_status()
            data = response.json()
            order_id = (data.get("data") or {}).get("order_id")
            return OrderResponse(
                accepted=True,
                status="submitted",
                broker_order_id=order_id,
                message="Live order submitted to Upstox.",
                payload=data,
            )
        except httpx.HTTPStatusError as exc:
            details = exc.response.text
            logger.error("Upstox order rejected: %s", details)
            return OrderResponse(
                accepted=False,
                status="rejected",
                broker_order_id=None,
                message=f"Upstox rejected the order: {details}",
                payload={"status_code": exc.response.status_code},
            )
        except Exception as exc:
            logger.exception("Upstox order request failed: %s", exc)
            return OrderResponse(
                accepted=False,
                status="failed",
                broker_order_id=None,
                message=f"Broker request failed: {exc}",
            )


def get_broker_adapter() -> BrokerAdapter:
    broker_name = settings.TRADING_BROKER.strip().lower()
    if broker_name == "upstox":
        return UpstoxBrokerAdapter()
    raise ValueError(f"Unsupported broker configured: {settings.TRADING_BROKER}")


def broker_status_dict() -> dict:
    status = get_broker_adapter().get_status()
    return asdict(status)


def payload_to_text(payload: Optional[dict]) -> Optional[str]:
    if payload is None:
        return None
    return json.dumps(payload, default=str)
