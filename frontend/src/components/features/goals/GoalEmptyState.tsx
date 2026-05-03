import { Target } from 'lucide-react';

interface GoalEmptyStateProps {
  onCreateClick: () => void;
}

export function GoalEmptyState({ onCreateClick }: GoalEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-[#f3f4f3]">
        <Target size={40} className="text-[#9ca3af]" />
      </div>
      <h3 className="text-lg font-semibold text-[#303333]">
        Aún no tienes objetivos de ahorro
      </h3>
      <p className="mt-2 max-w-sm text-sm text-[#5d605f]">
        Crea tu primer objetivo y empieza a ahorrar para lo que más te importa
      </p>
      <button
        onClick={onCreateClick}
        className="mt-6 rounded-full bg-[#0060ad] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#0052a3] transition-colors"
      >
        Crear mi primer objetivo
      </button>
    </div>
  );
}
