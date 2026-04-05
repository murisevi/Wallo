// Shared TypeScript interfaces matching backend Pydantic schemas.

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

export interface Transaction {
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
  category: string | null;
  account_iban: string | null;
}

export interface TransactionList {
  transactions: Transaction[];
  total: number;
  page: number;
  page_size: number;
}

export interface Dashboard {
  /** Decimal serialised as string */
  total_balance: string;
  currency: string;
  accounts: AccountSummary[];
  recent_transactions: Transaction[];
  last_synced_at: string | null;
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
