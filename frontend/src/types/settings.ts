// Settings-specific TypeScript interfaces matching backend schemas.

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  currency: 'EUR' | 'USD' | 'GBP';
  timezone: string;
  created_at: string;
}

export interface UserProfileUpdate {
  full_name?: string;
  email?: string;
  currency?: 'EUR' | 'USD' | 'GBP';
}

export interface BankConnection {
  id: string;
  bank_name: string;
  bank_country: string;
  bank_logo: string | null;
  status: string;
  accounts_count: number;
  last_synced_at: string | null;
  created_at: string;
}
