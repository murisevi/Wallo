'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { SankeyResponse } from '@/types/reports';

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });

// ─── Types ────────────────────────────────────────────────────────────────────

interface LayoutNode {
  id: string;
  label: string;
  color: string;
  column: 'left' | 'center' | 'right';
  // filled by d3-sankey
  x0: number;
  x1: number;
  y0: number;
  y1: number;
  [key: string]: unknown;
}

interface RawLink {
  source: LayoutNode | undefined;
  target: LayoutNode | undefined;
  value: number;
  // filled by d3-sankey
  width: number;
  index: number;
  y0: number;
  y1: number;
  [key: string]: unknown;
}

interface LayoutLink extends RawLink {
  source: LayoutNode;
  target: LayoutNode;
}

interface LayoutGraph {
  nodes: LayoutNode[];
  links: LayoutLink[];
}

// d3-sankey minimal typing (dynamic import — no SSR)
interface SankeyBuilder {
  nodeId: (fn: (d: LayoutNode) => string) => SankeyBuilder;
  nodeWidth: (w: number) => SankeyBuilder;
  nodePadding: (p: number) => SankeyBuilder;
  extent: (e: [[number, number], [number, number]]) => SankeyBuilder;
  (graph: { nodes: LayoutNode[]; links: RawLink[] }): LayoutGraph;
}
interface D3SankeyModule {
  sankey: () => SankeyBuilder;
}

interface TooltipState {
  x: number;
  y: number;
  text: string;
}

// ─── Colors ───────────────────────────────────────────────────────────────────

const INCOME_PALETTE = [
  '#2471A3',
  '#1A5276',
  '#5DADE2',
  '#117A65',
  '#148F77',
  '#1E8449',
  '#85C1E9',
  '#2E86C1',
  '#0E6655',
  '#A9CCE3',
];

const EXPENSE_COLORS: Record<string, string> = {
  vivienda: '#1B4F72',
  alimentación: '#5DADE2',
  alimentacion: '#5DADE2',
  ocio: '#E74C3C',
  transporte: '#2ECC71',
  salud: '#F39C12',
  educación: '#8E44AD',
  educacion: '#8E44AD',
  ropa: '#E67E22',
  tecnología: '#2980B9',
  tecnologia: '#2980B9',
  restaurantes: '#C0392B',
  'restaurantes y bares': '#C0392B',
  supermercado: '#27AE60',
  suscripciones: '#9B59B6',
  viajes: '#16A085',
  gimnasio: '#D35400',
  seguros: '#2C3E50',
  suministros: '#7F8C8D',
  'ocio y cenas': '#E74C3C',
  'otros gastos': '#95A5A6',
  'sin categoría': '#BDC3C7',
  'sin categoria': '#BDC3C7',
};
const CENTER_COLOR = '#5D6D7E';
const DEFAULT_EXPENSE_COLOR = '#95A5A6';

function expenseColor(label: string): string {
  return EXPENSE_COLORS[label.toLowerCase()] ?? DEFAULT_EXPENSE_COLOR;
}

// ─── Data transformation — build 3-column layout ──────────────────────────────

const MAX_INCOME = 8;
const MIN_INCOME_PCT = 0.025;
const MIN_EXPENSE_PCT = 0.015;
const CENTER_ID = 'center_flujo';

interface TransformedGraph {
  nodes: { id: string; label: string; column: 'left' | 'center' | 'right'; color: string }[];
  links: { source: string; target: string; value: number }[];
}

function buildGraph(data: SankeyResponse): TransformedGraph | null {
  if (!data.nodes.length || !data.links.length) return null;

  // Tally income source totals and expense category totals from backend links
  const incomeTotals = new Map<string, number>();
  const expenseTotals = new Map<string, number>();

  for (const lk of data.links) {
    const v = parseFloat(lk.value);
    incomeTotals.set(lk.source, (incomeTotals.get(lk.source) ?? 0) + v);
    expenseTotals.set(lk.target, (expenseTotals.get(lk.target) ?? 0) + v);
  }

  const labelOf = (id: string) => data.nodes.find((n) => n.id === id)?.label ?? id;

  const totalIncome = [...incomeTotals.values()].reduce((a, b) => a + b, 0);
  const totalExpenses = [...expenseTotals.values()].reduce((a, b) => a + b, 0);

  // ── Income sources: keep top MAX_INCOME above threshold, merge rest ──────
  const sortedIncome = [...incomeTotals.entries()].sort((a, b) => b[1] - a[1]);
  const mainIncome: { id: string; label: string; value: number }[] = [];
  let otherIncome = 0;
  for (const [id, v] of sortedIncome) {
    if (mainIncome.length < MAX_INCOME && v / totalIncome >= MIN_INCOME_PCT) {
      mainIncome.push({ id, label: labelOf(id), value: v });
    } else {
      otherIncome += v;
    }
  }
  if (otherIncome > 0.01) {
    mainIncome.push({ id: 'income_otros', label: 'Otros ingresos', value: otherIncome });
  }

  // ── Expense categories: merge small ones ─────────────────────────────────
  const sortedExpense = [...expenseTotals.entries()].sort((a, b) => b[1] - a[1]);
  const mainExpense: { id: string; label: string; value: number }[] = [];
  let otherExpense = 0;
  for (const [id, v] of sortedExpense) {
    if (v / totalExpenses >= MIN_EXPENSE_PCT) {
      mainExpense.push({ id, label: labelOf(id), value: v });
    } else {
      otherExpense += v;
    }
  }
  if (otherExpense > 0.01) {
    mainExpense.push({ id: 'cat_otros', label: 'Otros gastos', value: otherExpense });
  }

  const centerLabel = `Flujo de caja`;

  const nodes: TransformedGraph['nodes'] = [
    ...mainIncome.map((s, i) => ({
      id: s.id,
      label: s.label,
      column: 'left' as const,
      color: INCOME_PALETTE[i % INCOME_PALETTE.length],
    })),
    { id: CENTER_ID, label: centerLabel, column: 'center' as const, color: CENTER_COLOR },
    ...mainExpense.map((e) => ({
      id: e.id,
      label: e.label,
      column: 'right' as const,
      color: expenseColor(e.label),
    })),
  ];

  // Links: income → center (their actual total), center → expenses (their actual total)
  // d3-sankey accepts unbalanced nodes — it uses max(in, out) as node height
  const links: TransformedGraph['links'] = [
    ...mainIncome.map((s) => ({ source: s.id, target: CENTER_ID, value: s.value })),
    ...mainExpense.map((e) => ({
      source: CENTER_ID,
      target: e.id,
      value: Math.min(e.value, totalIncome),
    })),
  ];

  return { nodes, links };
}

// ─── SVG ribbon path ──────────────────────────────────────────────────────────

function ribbonPath(link: LayoutLink): string {
  const sx = link.source.x1;
  const tx = link.target.x0;
  const mx = (sx + tx) / 2;
  const hy = link.width / 2;
  const sy = link.y0;
  const ty = link.y1;

  return [
    `M ${sx},${sy - hy}`,
    `C ${mx},${sy - hy} ${mx},${ty - hy} ${tx},${ty - hy}`,
    `L ${tx},${ty + hy}`,
    `C ${mx},${ty + hy} ${mx},${sy + hy} ${sx},${sy + hy}`,
    `Z`,
  ].join(' ');
}

// ─── Component ────────────────────────────────────────────────────────────────

interface Props {
  data: SankeyResponse;
}

const LABEL_GAP = 10;
const NODE_WIDTH = 20;
const NODE_PADDING = 18;
const H_MARGIN = 168; // horizontal margin reserved for labels on each side

export default function CashflowSankeyChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgWidth, setSvgWidth] = useState(720);
  const [layout, setLayout] = useState<LayoutGraph | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [hoveredLinkIdx, setHoveredLinkIdx] = useState<number | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const graph = useMemo(() => buildGraph(data), [data]);

  const leftCount = graph?.nodes.filter((n) => n.column === 'left').length ?? 0;
  const rightCount = graph?.nodes.filter((n) => n.column === 'right').length ?? 0;
  const HEIGHT = Math.max(500, Math.max(leftCount, rightCount) * 58 + 100);

  // Track container width
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      setSvgWidth(entries[0].contentRect.width || 720);
    });
    ro.observe(el);
    setSvgWidth(el.getBoundingClientRect().width || 720);
    return () => ro.disconnect();
  }, []);

  // Compute d3-sankey layout
  useEffect(() => {
    if (!graph) {
      setLayout(null);
      return;
    }

    import('d3-sankey').then((d3s: D3SankeyModule) => {
      const colorMap = new Map(graph.nodes.map((n) => [n.id, n.color]));
      const columnMap = new Map(graph.nodes.map((n) => [n.id, n.column]));

      const nodes: LayoutNode[] = graph.nodes.map((n) => ({
        ...n,
        x0: 0,
        x1: 0,
        y0: 0,
        y1: 0,
        color: colorMap.get(n.id) ?? DEFAULT_EXPENSE_COLOR,
        column: columnMap.get(n.id) ?? 'right',
      }));

      const nodeById = new Map(nodes.map((n) => [n.id, n]));

      const rawLinks: RawLink[] = graph.links.map((l, i) => ({
        source: nodeById.get(l.source),
        target: nodeById.get(l.target),
        value: l.value,
        width: 0,
        index: i,
        y0: 0,
        y1: 0,
      }));

      const validLinks = rawLinks.filter((l) => l.source && l.target);

      const sankeyLayout = d3s
        .sankey()
        .nodeId((d: LayoutNode) => d.id)
        .nodeWidth(NODE_WIDTH)
        .nodePadding(NODE_PADDING)
        .extent([
          [H_MARGIN, 20],
          [svgWidth - H_MARGIN, HEIGHT - 20],
        ]);

      const computed = sankeyLayout({ nodes, links: validLinks });
      setLayout(computed as LayoutGraph);
    });
  }, [graph, svgWidth, HEIGHT]);

  if (!data.nodes.length) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-gray-400">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-10 w-10"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
          />
        </svg>
        <p className="text-sm">No hay datos para el período seleccionado</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full" style={{ height: HEIGHT }}>
      {layout && (
        <svg width={svgWidth} height={HEIGHT} style={{ overflow: 'visible' }}>
          <defs>
            {layout.links.map((link, i) => (
              <linearGradient
                key={i}
                id={`sg-${i}`}
                gradientUnits="userSpaceOnUse"
                x1={link.source.x1}
                x2={link.target.x0}
              >
                <stop offset="0%" stopColor={link.source.color} stopOpacity={0.55} />
                <stop offset="100%" stopColor={link.target.color} stopOpacity={0.55} />
              </linearGradient>
            ))}
          </defs>

          {/* ── Ribbons ─────────────────────────────────────────────── */}
          {layout.links.map((link, i) => {
            const isHovered =
              hoveredLinkIdx === i ||
              hoveredNodeId === link.source.id ||
              hoveredNodeId === link.target.id;
            return (
              <path
                key={i}
                d={ribbonPath(link)}
                fill={`url(#sg-${i})`}
                fillOpacity={isHovered ? 0.82 : 0.48}
                style={{ transition: 'fill-opacity 0.15s', cursor: 'pointer' }}
                onMouseEnter={(e) => {
                  setHoveredLinkIdx(i);
                  setTooltip({
                    x: e.clientX,
                    y: e.clientY,
                    text: `${link.source.label} → ${link.target.label}  ${fmt.format(link.value)}`,
                  });
                }}
                onMouseMove={(e) =>
                  setTooltip((t) => (t ? { ...t, x: e.clientX, y: e.clientY } : null))
                }
                onMouseLeave={() => {
                  setHoveredLinkIdx(null);
                  setTooltip(null);
                }}
              />
            );
          })}

          {/* ── Nodes + labels ──────────────────────────────────────── */}
          {layout.nodes.map((node) => {
            const isHovered = hoveredNodeId === node.id;
            const midY = (node.y0 + node.y1) / 2;
            const barH = Math.max(node.y1 - node.y0, 4);
            const isCenter = node.id === CENTER_ID;
            const isLeft = node.column === 'left';

            // Total value: for left nodes = outgoing, for center/right = incoming
            const nodeValue = layout.links
              .filter((l) => (isLeft ? l.source.id === node.id : l.target.id === node.id))
              .reduce((s, l) => s + l.value, 0);

            // Label placement
            const labelX = isLeft
              ? node.x0 - LABEL_GAP
              : isCenter
                ? (node.x0 + node.x1) / 2
                : node.x1 + LABEL_GAP;
            const anchor = isLeft ? 'end' : isCenter ? 'middle' : 'start';

            const rawLabel = node.label;
            const displayLabel =
              rawLabel.length > 22 ? `${rawLabel.slice(0, 20)}…` : rawLabel;

            return (
              <g
                key={node.id}
                style={{ cursor: 'pointer' }}
                onMouseEnter={(e) => {
                  setHoveredNodeId(node.id);
                  setTooltip({ x: e.clientX, y: e.clientY, text: `${node.label}: ${fmt.format(nodeValue)}` });
                }}
                onMouseMove={(e) =>
                  setTooltip((t) => (t ? { ...t, x: e.clientX, y: e.clientY } : null))
                }
                onMouseLeave={() => {
                  setHoveredNodeId(null);
                  setTooltip(null);
                }}
              >
                {/* Bar */}
                <rect
                  x={node.x0}
                  y={node.y0}
                  width={node.x1 - node.x0}
                  height={barH}
                  fill={node.color}
                  fillOpacity={isHovered ? 1 : 0.9}
                  rx={3}
                  style={{ transition: 'fill-opacity 0.15s' }}
                />
                {/* Name */}
                <text
                  x={labelX}
                  y={midY - 7}
                  dominantBaseline="middle"
                  textAnchor={anchor}
                  fontSize={isCenter ? 12 : 11}
                  fontWeight={600}
                  fill="#1f2937"
                >
                  {displayLabel}
                </text>
                {/* Amount */}
                <text
                  x={labelX}
                  y={midY + 7}
                  dominantBaseline="middle"
                  textAnchor={anchor}
                  fontSize={10}
                  fontWeight={400}
                  fill="#6b7280"
                >
                  {fmt.format(nodeValue)}
                </text>
              </g>
            );
          })}
        </svg>
      )}

      {/* Floating tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 max-w-xs rounded-lg bg-gray-900 px-3 py-1.5 text-xs text-white shadow-lg"
          style={{ left: tooltip.x + 14, top: tooltip.y - 34 }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
