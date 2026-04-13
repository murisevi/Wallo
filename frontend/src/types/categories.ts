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
  status: string;
  account_iban: string | null;
  // Categorization fields
  category_id: string | null;
  category: Category | null;
  category_name: string | null;
  category_icon: string | null;
  categorization_method: 'merchant_map' | 'ml_auto' | 'ml_suggested' | 'manual' | null;
  confidence_score: number | null;
  is_manually_corrected: boolean;
}

export interface CategoryCorrectionResponse {
  transaction_id: string;
  old_category_id: string | null;
  new_category_id: string;
  confidence_score: number;
}
