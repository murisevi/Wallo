'use client';

interface CategoryBadgeProps {
  name: string;
  /** Hex color from the category object, e.g. "#F97316" */
  color: string;
  confidence?: number | null;
  method?: string | null;
  /** If provided, the badge becomes a clickable button */
  onClick?: () => void;
}

/**
 * Pill badge for a transaction category.
 *
 * - Background: 12% opacity tint of `color` (CSS hex + "20").
 * - Text: `color` at full opacity.
 * - Low-confidence suggestion (method = "ml_suggested" and confidence < 0.7):
 *   dashed border + "?" suffix to signal the user should confirm or correct.
 */
export function CategoryBadge({
  name,
  color,
  confidence,
  method,
  onClick,
}: CategoryBadgeProps) {
  const isSuggested = method === 'ml_suggested' && (confidence ?? 0) < 0.7;

  const Tag = onClick ? 'button' : 'span';

  return (
    <Tag
      onClick={onClick}
      title={
        isSuggested
          ? 'Categoría sugerida — haz clic para confirmar o cambiar'
          : undefined
      }
      className={[
        'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold',
        isSuggested ? 'border border-dashed' : '',
        onClick ? 'cursor-pointer transition-opacity hover:opacity-75' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      style={{
        backgroundColor: `${color}20`,
        color,
        borderColor: isSuggested ? color : undefined,
      }}
    >
      {name}
      {isSuggested && (
        <span className="font-bold opacity-60" aria-label="sugerida">
          ?
        </span>
      )}
    </Tag>
  );
}
