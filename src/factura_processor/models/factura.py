from pydantic import BaseModel


class Factura(BaseModel):
    """Structured invoice data returned by the AI extractor."""

    numero_factura: str = ""
    fecha_factura: str = ""        # YYYY-MM-DD
    emisor: str = ""               # Supplier name
    nif_cif: str = ""
    importe_neto: float = 0.0
    iva: float = 0.0
    total: float = 0.0
    fecha_vencimiento: str = ""    # YYYY-MM-DD
    descripcion: str = ""
    clave_unica: str = ""          # numero_factura + "|" + emisor
