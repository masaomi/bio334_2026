"""QR code rendering for handle distribution.

Returns a data: URL embedding a PNG. Used at registration time to print
``https://<host>/?u=<handle>`` as a scannable code alongside the
clickable URL and paper-memo handle (3-channel distribution per
ARCHITECTURE.md §5.2).
"""

from __future__ import annotations

import base64
from io import BytesIO


def qr_data_url(text: str) -> str:
    """Return a ``data:image/png;base64,...`` URL for a QR code of ``text``."""
    import qrcode

    img = qrcode.make(text)
    buf = BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
