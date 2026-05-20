// Category domain TypeScript interfaces — mirrors backend app/categories/schemas.py

export interface Category {
  id: string;
  name: string;
  icon: string;
  color: string;
  type: 'expense' | 'income';
  is_custom: boolean;
}

/** Mirrors TransactionResponse with categorization fields populated. */
export interface TransactionWithCategory {
  id: string;
  account_id: string;
  entry_reference: string | null;
  /** Decimal serialised as string — signed: positive = CRDT, negative = DBIT */
  amount: string;
  currency: string;
  /** ISO 8601 date string */
  date: string;
  value_date: string | null;
  description: string | null;
  debtor_name: string | null;
  creditor_name: string | null;
  credit_debit_indicator: 'CRDT' | 'DBIT';
  bank_transaction_code: string | null;
  merchant_category_code: string | null;
  status: string;
  account_iban: string | null;
  // Categorization fields
  category_id: string | null;
  category: Category | null;
  category_name: string | null;
  category_icon: string | null;
  categorization_method:
    | 'rule_based'
    | 'merchant_map'
    | 'mcc'
    | 'global_dict'
    | 'keyword_rule'
    | 'ml_auto'
    | 'manual'
    | null;
  confidence_score: number | null;
  is_manually_corrected: boolean;
  suggested_category_id: string | null;
  suggested_category: Category | null;
  suggested_category_name: string | null;
  suggested_category_icon: string | null;
  suggested_categorization_method: 'ml_suggested' | 'keyword_suggested' | null;
  suggested_confidence_score: number | null;
}

export interface CategoryCorrectionResponse {
  transaction_id: string;
  old_category_id: string | null;
  new_category_id: string;
  confidence_score: number;
  also_updated: number;
}
