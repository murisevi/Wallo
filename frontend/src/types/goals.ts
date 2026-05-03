// frontend/src/types/goals.ts
// Decimal fields serialised as string by FastAPI. Create/Update use number (user input).

export interface SavingsGoal {
  id: string;
  user_id: string;
  name: string;
  icon: string;
  color: string;
  /** Decimal → string */
  target_amount: string;
  /** Decimal → string */
  current_amount: string;
  /** Decimal → string | null */
  monthly_contribution: string | null;
  deadline: string | null;
  priority: number;
  status: 'active' | 'completed' | 'cancelled';
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  // Computed fields
  percentage: number;
  days_remaining: number | null;
  estimated_completion_date: string | null;
  pace_status: 'on_track' | 'ahead' | 'at_risk' | null;
  motivational_message: string;
  recent_contributions: GoalContribution[];
}

export interface GoalContribution {
  id: string;
  goal_id: string;
  /** Decimal → string */
  amount: string;
  note: string | null;
  created_at: string;
}

export interface GoalSummary {
  goals: SavingsGoal[];
  /** Decimal → string */
  total_saved: string;
  /** Decimal → string */
  total_target: string;
  active_count: number;
  completed_count: number;
}

export interface GoalCreate {
  name: string;
  target_amount: number;
  icon?: string;
  color?: string;
  monthly_contribution?: number | null;
  deadline?: string | null;
  priority?: number;
}

export interface GoalUpdate {
  name?: string;
  target_amount?: number;
  icon?: string;
  color?: string;
  monthly_contribution?: number | null;
  deadline?: string | null;
  priority?: number;
  status?: 'active' | 'completed' | 'cancelled';
}

export interface ContributionCreate {
  amount: number;
  note?: string | null;
}
