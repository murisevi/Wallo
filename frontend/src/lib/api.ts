import type { Budget, BudgetCreate, BudgetSummary, BudgetUpdate, CopySource } from '@/types/budget';
import type { Category, CategoryCorrectionResponse } from '@/types/categories';
import type {
  ContributionCreate,
  GoalContribution,
  GoalCreate,
  GoalStatus,
  GoalSummary,
  GoalUpdate,
  SavingsGoal,
} from '@/types/goals';
import type { RecurringCharge } from '@/types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) ?? {}),
  };

  // Attach JWT if available (client-side only)
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Clear the stored token and notify auth listeners (e.g. to redirect to /login)
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      window.dispatchEvent(new CustomEvent('wallo:unauthorized'));
    }
    throw new ApiError(401, 'Unauthorized');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, (body as { detail?: string }).detail ?? res.statusText);
  }

  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'GET' });
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },

  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' });
  },

  async getBlob(path: string): Promise<Blob> {
    const headers: Record<string, string> = {};
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${BASE_URL}${path}`, { method: 'GET', headers });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, (body as { detail?: string }).detail ?? res.statusText);
    }
    return res.blob();
  },
};

// ─── Budget endpoints ────────────────────────────────────────────────────────

export const budgetApi = {
  getCategories(): Promise<Category[]> {
    return api.get<Category[]>('/budgets/categories');
  },

  getSummary(month: number, year: number): Promise<BudgetSummary> {
    return api.get<BudgetSummary>(`/budgets/?month=${month}&year=${year}`);
  },

  createBudget(data: BudgetCreate): Promise<Budget> {
    return api.post<Budget>('/budgets/', data);
  },

  updateBudget(id: string, data: BudgetUpdate): Promise<Budget> {
    return api.put<Budget>(`/budgets/${id}`, data);
  },

  deleteBudget(id: string): Promise<void> {
    return api.delete<void>(`/budgets/${id}`);
  },

  getCopySource(month: number, year: number): Promise<CopySource> {
    return api.get<CopySource>(`/budgets/copy-source?month=${month}&year=${year}`);
  },

  copyPrevious(month: number, year: number): Promise<BudgetSummary> {
    return api.post<BudgetSummary>(`/budgets/copy-previous?month=${month}&year=${year}`);
  },
};

// ─── Category endpoints ──────────────────────────────────────────────────────

export const categoryApi = {
  /** List all system categories + the authenticated user's custom ones. */
  getCategories(): Promise<Category[]> {
    return api.get<Category[]>('/categories/');
  },

  /** Create a custom category owned by the current user. */
  createCategory(data: {
    name: string;
    icon: string;
    color: string;
    type: 'expense' | 'income';
  }): Promise<Category> {
    return api.post<Category>('/categories/', data);
  },

  /** Submit an active-learning correction for a transaction's category. */
  correctTransactionCategory(
    transactionId: string,
    categoryId: string,
  ): Promise<CategoryCorrectionResponse> {
    return api.patch<CategoryCorrectionResponse>(
      `/categories/transactions/${transactionId}/category`,
      { category_id: categoryId },
    );
  },

  /** Accept visible suggested categories through the active-learning endpoint. */
  acceptSuggestions(transactionIds: string[]): Promise<{
    accepted: number;
    skipped: number;
    also_updated: number;
  }> {
    return api.post('/categories/suggestions/accept', {
      transaction_ids: transactionIds,
    });
  },
};

// ─── Recurring charges endpoints ─────────────────────────────────────────────

export const recurringApi = {
  list(): Promise<RecurringCharge[]> {
    return api.get<RecurringCharge[]>('/recurring-charges/');
  },

  confirm(id: string): Promise<RecurringCharge> {
    return api.patch<RecurringCharge>(`/recurring-charges/${id}/confirm`);
  },

  dismiss(id: string): Promise<void> {
    return api.patch<void>(`/recurring-charges/${id}/dismiss`);
  },

  setInstallment(id: string, installment_total: number): Promise<RecurringCharge> {
    return api.patch<RecurringCharge>(`/recurring-charges/${id}/installment`, {
      installment_total,
    });
  },

  delete(id: string): Promise<void> {
    return api.delete<void>(`/recurring-charges/${id}`);
  },
};

// ─── Goals endpoints ─────────────────────────────────────────────────────────

export const goalsApi = {
  list(status?: GoalStatus | 'all'): Promise<GoalSummary> {
    const qs = status && status !== 'all' ? `?status=${status}` : '';
    return api.get<GoalSummary>(`/goals/${qs}`);
  },

  get(id: string): Promise<SavingsGoal> {
    return api.get<SavingsGoal>(`/goals/${id}`);
  },

  create(data: GoalCreate): Promise<SavingsGoal> {
    return api.post<SavingsGoal>('/goals/', data);
  },

  update(id: string, data: GoalUpdate): Promise<SavingsGoal> {
    return api.patch<SavingsGoal>(`/goals/${id}`, data);
  },

  delete(id: string): Promise<void> {
    return api.delete<void>(`/goals/${id}`);
  },

  addContribution(id: string, data: ContributionCreate): Promise<SavingsGoal> {
    return api.post<SavingsGoal>(`/goals/${id}/contributions`, data);
  },

  getContributions(id: string): Promise<GoalContribution[]> {
    return api.get<GoalContribution[]>(`/goals/${id}/contributions`);
  },
};

export { ApiError };
