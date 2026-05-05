"""Invoice data extraction backed by xAI (Grok) via the OpenAI-compatible SDK."""

import json
import logging

from openai import OpenAI

from ...config import Settings
from ...models import Factura
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_XAI_BASE_URL = "https://api.x.ai/v1"


def extract_invoice_data(pdf_text: str, settings: Settings) -> Factura:
    """Send the PDF text to xAI (Grok) and return a structured Factura.

    The call relies on:
    - response_format=json_object  → guarantees a JSON-only reply
    - a detailed system prompt with the schema spelled out
    """
    client = OpenAI(
        api_key=settings.xai_api_key,
        base_url=_XAI_BASE_URL,
    )

    response = client.chat.completions.create(
        model=settings.ai_model,
        max_tokens=1024,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Extrae todos los campos de la siguiente factura y devuelve el JSON.\n\n"
                    f"TEXTO DE LA FACTURA:\n{pdf_text}"
                ),
            },
        ],
    )

    usage = response.usage
    logger.debug(
        "xAI tokens — prompt: %d | completion: %d | total: %d",
        usage.prompt_tokens,
        usage.completion_tokens,
        usage.total_tokens,
    )

    data: dict = json.loads(response.choices[0].message.content)
    data["clave_unica"] = f"{data['numero_factura']}|{data['emisor']}"

    factura = Factura(**data)
    logger.info(
        "Invoice extracted → key: '%s' | total: %.2f",
        factura.clave_unica,
        factura.total,
    )
    return factura
