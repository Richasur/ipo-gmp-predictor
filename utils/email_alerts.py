"""
email_alerts.py — Gmail SMTP alert system
Sends email when STRONG BUY signals are detected.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

GMAIL_USER  = os.environ.get("GMAIL_USER", "")
GMAIL_PASS  = os.environ.get("GMAIL_PASS", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", GMAIL_USER)


def send_strong_buy_alert(strong_buys: list) -> bool:
    """
    Send an email alert for STRONG BUY IPO signals.
    Returns True if sent successfully, False otherwise.
    """
    if not GMAIL_USER or not GMAIL_PASS:
        logger.warning("[alert] GMAIL_USER / GMAIL_PASS not set — skipping email")
        return False

    subject = f"🚀 IPO GMP Alert: {len(strong_buys)} STRONG BUY Signal(s) — {datetime.now().strftime('%d %b %Y %H:%M')}"

    # ── Build HTML body ───────────────────────────────────
    rows_html = ""
    for s in strong_buys:
        rows_html += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #2d2d2d;font-weight:600">{s.ipo_name}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #2d2d2d;text-align:center">{s.score}/40</td>
          <td style="padding:8px 12px;border-bottom:1px solid #2d2d2d;text-align:center">
            <span style="background:#00c853;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">
              {s.signal}
            </span>
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #2d2d2d;text-align:center">{s.confidence}%</td>
          <td style="padding:8px 12px;border-bottom:1px solid #2d2d2d;color:#aaa;font-size:12px">{", ".join(s.reasons)}</td>
        </tr>"""

    html_body = f"""
    <html>
    <body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#eee;margin:0;padding:20px">
      <div style="max-width:700px;margin:auto;background:#1a1a1a;border-radius:12px;padding:24px;
                  border:1px solid #2d2d2d">
        <h2 style="color:#00c853;margin-top:0">🚀 IPO GMP Predictor — STRONG BUY Alert</h2>
        <p style="color:#aaa">{datetime.now().strftime("%d %B %Y, %H:%M IST")}</p>

        <table style="width:100%;border-collapse:collapse;margin-top:16px">
          <thead>
            <tr style="background:#252525">
              <th style="padding:10px 12px;text-align:left;color:#888;font-size:12px;text-transform:uppercase">IPO</th>
              <th style="padding:10px 12px;text-align:center;color:#888;font-size:12px;text-transform:uppercase">Score</th>
              <th style="padding:10px 12px;text-align:center;color:#888;font-size:12px;text-transform:uppercase">Signal</th>
              <th style="padding:10px 12px;text-align:center;color:#888;font-size:12px;text-transform:uppercase">Confidence</th>
              <th style="padding:10px 12px;text-align:left;color:#888;font-size:12px;text-transform:uppercase">Reasons</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>

        <p style="margin-top:24px;color:#555;font-size:11px">
          Data sourced from ipowatch.in · Not financial advice · IPO GMP Predictor
        </p>
      </div>
    </body>
    </html>"""

    # ── Send via Gmail SMTP ───────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = ALERT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, ALERT_EMAIL, msg.as_string())
        logger.info(f"[alert] Email sent to {ALERT_EMAIL}")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"[alert] SMTP error: {e}")
        return False
