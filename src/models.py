from typing import Any, Optional
from pydantic import BaseModel, Field


class Vendor(BaseModel):
    vendor_id: Optional[str] = None
    name: str
    gstin: Optional[str] = None
    state: Optional[str] = None
    bank: Optional[str] = None
    ifsc: Optional[str] = None
    source_pages: list[int] = Field(default_factory=list)


class InvoiceLineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class Invoice(BaseModel):
    invoice_id: str
    vendor_name: Optional[str] = None
    invoice_date: Optional[str] = None
    po_reference: Optional[str] = None
    total_amount: Optional[float] = None
    gstin: Optional[str] = None
    ifsc: Optional[str] = None
    line_items: list[InvoiceLineItem] = Field(default_factory=list)
    source_pages: list[int] = Field(default_factory=list)


class PurchaseOrder(BaseModel):
    po_id: str
    vendor_name: Optional[str] = None
    po_date: Optional[str] = None
    total_amount: Optional[float] = None
    source_pages: list[int] = Field(default_factory=list)


class BankTxn(BaseModel):
    txn_id: str
    txn_date: Optional[str] = None
    vendor_name: Optional[str] = None
    amount: Optional[float] = None
    reference: Optional[str] = None
    source_pages: list[int] = Field(default_factory=list)


class ExpenseClaim(BaseModel):
    claim_id: str
    employee_id: Optional[str] = None
    claim_date: Optional[str] = None
    amount: Optional[float] = None
    source_pages: list[int] = Field(default_factory=list)


class Finding(BaseModel):
    finding_id: str
    category: str
    pages: list[int]
    document_refs: list[str]
    description: str
    reported_value: Optional[str] = None
    correct_value: Optional[str] = None
    confidence: float = 0.0
    evidence: dict[str, Any] = Field(default_factory=dict)