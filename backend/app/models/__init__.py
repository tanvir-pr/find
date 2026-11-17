"""Import all models so Alembic and metadata see every table."""

from app.models.branch import Branch
from app.models.commission import CommissionEntry, CommissionRule
from app.models.customer import Customer
from app.models.logistics import Delivery, Van
from app.models.product import Batch, Product, ProductVariant
from app.models.sales import Payment, Return, Sale, SaleItem
from app.models.shift import CashClosing, Shift
from app.models.stock import StockCount, StockCountLine, StockMovement
from app.models.supplier import PurchaseInvoice, Supplier
from app.models.system import KnowledgeChunk, ReceiptLog, SmsLog, SyncLog
from app.models.user import User

__all__ = [
    "Batch",
    "Branch",
    "CashClosing",
    "CommissionEntry",
    "CommissionRule",
    "Customer",
    "Delivery",
    "KnowledgeChunk",
    "Payment",
    "Product",
    "ProductVariant",
    "PurchaseInvoice",
    "ReceiptLog",
    "Return",
    "Sale",
    "SaleItem",
    "Shift",
    "SmsLog",
    "StockCount",
    "StockCountLine",
    "StockMovement",
    "Supplier",
    "SyncLog",
    "User",
    "Van",
]
