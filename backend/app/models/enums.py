import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    staff = "staff"


class StockMovementType(str, enum.Enum):
    purchase = "purchase"
    sale = "sale"
    customer_return = "return"
    damage = "damage"
    adjustment = "adjustment"


class PaymentType(str, enum.Enum):
    sale = "sale"
    customer_collection = "customer_collection"
    supplier_payment = "supplier_payment"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    bkash = "bkash"
    nagad = "nagad"
    credit = "credit"


class DeliveryStatus(str, enum.Enum):
    pending = "pending"
    in_transit = "in_transit"
    delivered = "delivered"
    cancelled = "cancelled"


class SmsPurpose(str, enum.Enum):
    daily_summary = "daily_summary"
    due_reminder = "due_reminder"
    offer = "offer"
    other = "other"


class SyncStatus(str, enum.Enum):
    pending = "pending"
    synced = "synced"
    conflict = "conflict"


class CommissionBasis(str, enum.Enum):
    percent_of_sale = "percent_of_sale"
    fixed_per_sale = "fixed_per_sale"


class AgentActionKind(str, enum.Enum):
    due_reminders = "due_reminders"
    daily_summary_sms = "daily_summary_sms"
    low_stock_alert = "low_stock_alert"
    expiring_alert = "expiring_alert"
    reorder_draft = "reorder_draft"


class AgentActionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    executed = "executed"
    failed = "failed"
    skipped = "skipped"


class AgentActionMode(str, enum.Enum):
    auto = "auto"
    approval = "approval"
