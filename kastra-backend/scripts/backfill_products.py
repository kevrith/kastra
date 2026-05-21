"""
Backfill products table from existing quotation and invoice items.
Run once from kastra-backend/:
    python -m scripts.backfill_products
"""
import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import AsyncSessionLocal
from app.models.product import Product


async def backfill():
    async with AsyncSessionLocal() as db:
        # Pull (org_id, description, unit_price) from all quotation items
        qt_rows = (await db.execute(text("""
            SELECT qi.description, qi.unit_price, q.organization_id
            FROM quotation_items qi
            JOIN quotations q ON q.id = qi.quotation_id
        """))).all()

        # Pull same from invoice items
        inv_rows = (await db.execute(text("""
            SELECT ii.description, ii.unit_price, i.organization_id
            FROM invoice_items ii
            JOIN invoices i ON i.id = ii.invoice_id
        """))).all()

        # Merge — last write wins per (org_id, description)
        catalog: dict[tuple, Decimal] = {}
        for desc, price, org_id in [*qt_rows, *inv_rows]:
            catalog[(str(org_id), desc)] = Decimal(str(price))

        count = 0
        for (org_id, name), unit_price in catalog.items():
            stmt = pg_insert(Product).values(
                id=uuid.uuid4(),
                organization_id=org_id,
                name=name,
                unit_price=unit_price,
            ).on_conflict_do_update(
                index_elements=["organization_id", "name"],
                set_={"unit_price": unit_price},
            )
            await db.execute(stmt)
            count += 1

        await db.commit()
        print(f"Backfilled {count} products.")


if __name__ == "__main__":
    asyncio.run(backfill())
