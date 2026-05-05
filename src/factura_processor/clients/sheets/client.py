"""Google Sheets sync — every run flushes invoices via a single batchUpdate call."""

import logging
from datetime import date

from googleapiclient.discovery import build

from ...config import Settings
from ...models import Factura
from ...utils import get_google_credentials

logger = logging.getLogger(__name__)

# Spreadsheet columns, in order.
_HEADERS = [
    "clave_unica",
    "numero_factura",
    "fecha_factura",
    "emisor",
    "nif_cif",
    "importe_neto",
    "iva",
    "total",
    "fecha_vencimiento",
    "descripcion",
    "fecha_procesado",
]

_LAST_COL = chr(ord("A") + len(_HEADERS) - 1)  # "K"


class SheetsClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.spreadsheet_id = settings.spreadsheet_id
        self.sheet_name = settings.sheet_name
        creds = get_google_credentials(settings)
        self._service = build("sheets", "v4", credentials=creds)

    # ── Public API ─────────────────────────────────────────────────────────────

    def sync_facturas(self, facturas: list[Factura]) -> None:
        """Upsert invoices into the sheet with a single batchUpdate call.

        Steps:
        1. Read every existing row (one call).
        2. Decide per clave_unica whether to update an existing row or append.
        3. Push all changes in a single batchUpdate.
        """
        self._ensure_headers()
        existing_rows = self._read_all()

        # Map clave_unica → 1-based row number (data starts at row 2).
        clave_to_row: dict[str, int] = {}
        for i, row in enumerate(existing_rows, start=2):
            if row and row[0]:
                clave_to_row[row[0]] = i

        next_new_row = len(existing_rows) + 2  # first free row after the data
        update_data: list[dict] = []

        for factura in facturas:
            row_values = self._factura_to_row(factura)

            if factura.clave_unica in clave_to_row:
                row_num = clave_to_row[factura.clave_unica]
                range_notation = f"{self.sheet_name}!A{row_num}:{_LAST_COL}{row_num}"
                logger.info("Updating row %d: %s", row_num, factura.clave_unica)
            else:
                range_notation = f"{self.sheet_name}!A{next_new_row}:{_LAST_COL}{next_new_row}"
                logger.info("Inserting new row %d: %s", next_new_row, factura.clave_unica)
                next_new_row += 1

            update_data.append({"range": range_notation, "values": [row_values]})

        if not update_data:
            logger.info("Nothing to sync")
            return

        self._service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": update_data,
            },
        ).execute()

        logger.info("batchUpdate done: %d row(s) written", len(update_data))

    # ── Private helpers ────────────────────────────────────────────────────────

    def _ensure_headers(self) -> None:
        """Write the header row if the sheet is empty."""
        result = (
            self._service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1:{_LAST_COL}1",
            )
            .execute()
        )
        if not result.get("values"):
            self._service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1:{_LAST_COL}1",
                valueInputOption="RAW",
                body={"values": [_HEADERS]},
            ).execute()
            logger.info("Wrote headers to '%s'", self.sheet_name)

    def _read_all(self) -> list[list[str]]:
        """Read every data row, skipping the header."""
        result = (
            self._service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A2:{_LAST_COL}",
            )
            .execute()
        )
        return result.get("values", [])

    @staticmethod
    def _factura_to_row(factura: Factura) -> list:
        trimestre: str = factura.fecha_factura.split("-")[1] if factura.fecha_factura else "00"
        match trimestre:
            case "01" | "02" | "03":
                trimestre = "T1"
            case "04" | "05" | "06":
                trimestre = "T2"
            case "07" | "08" | "09":
                trimestre = "T3"
            case "10" | "11" | "12":
                trimestre = "T4"
            case _:
                trimestre = ""
        return [
            factura.clave_unica,
            factura.fecha_factura,
            factura.emisor,
            factura.descripcion,
            trimestre,
            factura.importe_neto,
            factura.iva,
            factura.total,
            "",
            "",
            factura.nif_cif
        ]
