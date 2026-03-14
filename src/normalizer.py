def normalize_documents(raw_docs: list[dict]) -> dict:
    return {
        "vendors": [],
        "invoices": [],
        "purchase_orders": [],
        "bank_transactions": [],
        "expense_claims": [],
    }