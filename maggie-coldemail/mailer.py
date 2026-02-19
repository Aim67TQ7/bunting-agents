"""SMTP mailer for routing drafts to internal review."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from models import DraftEmail

log = logging.getLogger("maggie-coldemail.mailer")


class SmtpMailer:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        use_tls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls

    def send_draft(self, draft: DraftEmail, reviewer_email: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.from_email
        msg["To"] = reviewer_email
        msg["Subject"] = draft.subject
        msg.set_content(draft.text_body)
        msg.add_alternative(draft.html_body, subtype="html")

        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(msg)
        log.info("Draft routed to reviewer for customer %s", draft.customer_name)
