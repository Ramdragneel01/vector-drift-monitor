"""Webhook alerter (fire-and-forget; must never crash the service)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)


class Alerter:
    def fire(self, report) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class NoopAlerter(Alerter):
    def fire(self, report) -> None:
        log.info("alert(noop): %s severity=%s reasons=%s", report.namespace, report.severity, report.reasons)


@dataclass
class WebhookAlerter(Alerter):
    url: str

    def fire(self, report) -> None:
        if not self.url:
            return
        try:
            httpx.post(
                self.url,
                json={
                    "text": f":rotating_light: vector drift on `{report.namespace}` "
                            f"severity={report.severity} reasons={report.reasons}",
                    "report": report.to_dict(),
                },
                timeout=3.0,
            )
        except Exception as exc:
            log.warning("alert webhook failed: %s", exc)


def build_alerter(webhook_url: str) -> Alerter:
    return WebhookAlerter(webhook_url) if webhook_url else NoopAlerter()
