"""SMS/email notify adapters (mock OK for demos)."""

from app.integrations.notify.email import send_email
from app.integrations.notify.sms import send_sms

__all__ = ["send_sms", "send_email"]
