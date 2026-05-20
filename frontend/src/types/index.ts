// Shared TypeScript interfaces matching backend Pydantic schemas.

import type { Category } from '@/types/categories';
import type { SavingsGoal } from '@/types/goals';

export type { Category } from '@/types/categories';
export type { SavingsGoal } from '@/types/goals';

export interface User {
  id: string;
  email: string;
  name: string;
  currency: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AccountSummary {
  id: string;
  iban: string | null;
  name: string | null;
  bank_name: string;
  bank_logo: string | null;
  /** Decimal serialised as string by FastAPI */
  balance: string | null;
  currency: string;
}

/** Matches BankAccountResponse from backend banking/schemas.py */
export interface BankAccount {
  id: string;
  iban: string | null;
  name: string | null;
  account_type: string | null;
  currency: string;
  /** Decimal serialised as string */
  balance_amount: string | null;
  balance_type: string | null;
  last_synced_at: string | null;
}

export interface Transaction {
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

export interface TransactionList {
  transactions: Transaction[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RecurringCharge {
  id: string;
  display_name: string;
  /** Decimal serialised as string */
  amount: string;
  currency: string;
  periodicity: 'WEEKLY' | 'MONTHLY' | 'ANNUAL';
  status: 'possible' | 'confirmed' | 'dismissed';
  user_confirmed: boolean;
  occurrence_count: number;
  /** ISO date string */
  next_predicted_date: string;
  is_installment: boolean;
  installment_total: number | null;
  installment_paid: number | null;
}

export interface Dashboard {
  /** Decimal serialised as string */
  total_balance: string;
  /** Decimal serialised as string */
  reserved_for_goals: string;
  /** Decimal serialised as string */
  available_balance: string;
  currency: string;
  accounts: AccountSummary[];
  recent_transactions: Transaction[];
  last_synced_at: string | null;
  upcoming_charges: RecurringCharge[];
  active_goal: SavingsGoal | null;
}

export interface BankInstitution {
  name: string;
  country: string;
  logo: string | null;
}

export interface ConnectBankResponse {
  url: string;
  authorization_id: string;
}
