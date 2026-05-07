"""Top-level orchestrator for the invoice processing pipeline."""

import logging

from .clients.claude import extract_invoice_data
from .clients.gmail import GmailClient
from .clients.sheets import SheetsClient
from .config import Settings
from .models import Factura
from .tools import extract_text_from_pdf, save_invoice_pdf


def main() -> None:
    settings = Settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("factura-processor — starting")
    logger.info("=" * 60)

    gmail = GmailClient(settings)
    sheets = SheetsClient(settings)

    # 1. Find unread emails carrying PDF invoices.
    emails = gmail.get_invoice_emails()
    if not emails:
        logger.info("No invoice emails found. Done.")
        return

    facturas: list[Factura] = []

    for email in emails:
        logger.info("── Email: '%s'", email.subject or "(no subject)")

        for attachment in email.attachments:
            logger.info("   Processing attachment: %s", attachment.filename)

            # 2. Pull text out of the PDF locally with pypdfium2.
            try:
                pdf_text = extract_text_from_pdf(attachment.data)
            except Exception:
                logger.exception("   Failed to extract text from %s", attachment.filename)
                continue

            if not pdf_text.strip():
                logger.warning(
                    "   '%s' has no extractable text (scanned PDF?). Skipping.",
                    attachment.filename,
                )
                continue

            # 3. Hand the text to xAI (Grok) and get structured JSON back.
            try:
                factura = extract_invoice_data(pdf_text, settings)
                facturas.append(factura)
            except Exception:
                logger.exception("   xAI extraction failed for: %s", attachment.filename)
                continue

            # 4. Archive the PDF locally, grouped by issuer.
            try:
                save_invoice_pdf(
                    attachment.data,
                    attachment.filename,
                    factura.emisor,
                    settings.invoices_dir,
                )
            except Exception:
                logger.exception("   Could not save PDF %s to disk", attachment.filename)

        # 5. Flag the email as processed in Gmail.
        try:
            gmail.mark_as_processed(email.id)
        except Exception:
            logger.exception("   Could not mark email %s as processed", email.id)

    if not facturas:
        logger.info("No valid invoices were extracted. Done.")
        return

    # 6. Push everything to Google Sheets in a single batchUpdate.
    logger.info("Syncing %d invoice(s) to Google Sheets…", len(facturas))
    try:
        sheets.sync_facturas(facturas)
    except Exception:
        logger.exception("Google Sheets sync failed")
        raise

    logger.info("=" * 60)
    logger.info("Done. %d invoice(s) processed.", len(facturas))
    logger.info("=" * 60)
