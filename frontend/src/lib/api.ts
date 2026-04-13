import type { Budget, BudgetCreate, BudgetSummary, BudgetUpdate } from '@/types/budget';
import type { Category, CategoryCorrectionResponse } from '@/types/categories';

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
};

export { ApiError };
