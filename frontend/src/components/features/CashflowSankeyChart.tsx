'use client';

import { useEffect, useRef, useState } from 'react';
import type { SankeyResponse } from '@/types/reports';

const fmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

// Typed shapes after d3-sankey layout fills geometry in-place
interface LayoutNode {
  id: string;
  label: string;
  color: string;
  x0: number;
  x1: number;
  y0: number;
  y1: number;
}

interface LayoutLink {
  source: LayoutNode;
  target: LayoutNode;
  width: number;
  value: number;
  index: number;
  y0: number;
  y1: number;
}

interface LayoutGraph {
  nodes: LayoutNode[];
  links: LayoutLink[];
}

interface TooltipState {
  x: number;
  y: number;
  text: string;
}

const INCOME_COLOR = '#2ECC71';
const CATEGORY_COLORS: Record<string, string> = {
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
  supermercado: '#27AE60',
  'sin categoría': '#BDC3C7',
  'sin categoria': '#BDC3C7',
};

function getCategoryColor(label: string): string {
  return CATEGORY_COLORS[label.toLowerCase()] ?? '#95A5A6';
}

interface Props {
  data: SankeyResponse;
}

export default function CashflowSankeyChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);
  const [layout, setLayout] = useState<LayoutGraph | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [hoveredLink, setHoveredLink] = useState<number | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const HEIGHT = 420;

  // Observe container width
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      setWidth(entries[0].contentRect.width || 600);
    });
    observer.observe(el);
    setWidth(el.getBoundingClientRect().width || 600);
    return () => observer.disconnect();
  }, []);

  // Compute sankey layout whenever data or width changes
  useEffect(() => {
    if (!data.nodes.length || !data.links.length) {
      setLayout(null);
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    import('d3-sankey').then((d3s: any) => {
      const isIncome = (id: string) => id.startsWith('income_');

      const sankeyLayout = d3s
        .sankey()
        .nodeId((d: LayoutNode) => d.id)
        .nodeWidth(18)
        .nodePadding(14)
        .extent([
          [24, 16],
          [width - 24, HEIGHT - 16],
        ]);

      const nodes: LayoutNode[] = data.nodes.map((n) => ({
        ...n,
        color: isIncome(n.id) ? INCOME_COLOR : getCategoryColor(n.label),
        x0: 0, x1: 0, y0: 0, y1: 0,
      }));

      const nodeById = new Map(nodes.map((n) => [n.id, n]));

      const rawLinks = data.links
        .map((l, i) => ({
          source: nodeById.get(l.source),
          target: nodeById.get(l.target),
          value: parseFloat(l.value),
          width: 0,
          index: i,
          y0: 0,
          y1: 0,
        }))
        .filter((l) => l.source && l.target);

      const graph = sankeyLayout({ nodes, links: rawLinks }) as LayoutGraph;
      setLayout(graph);
    });
  }, [data, width]);

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
        <svg width={width} height={HEIGHT} className="overflow-visible">
          <defs>
            {layout.links.map((link, i) => (
              <linearGradient
                key={i}
                id={`grad-${i}`}
                gradientUnits="userSpaceOnUse"
                x1={link.source.x1}
                x2={link.target.x0}
              >
                <stop offset="0%" stopColor={link.source.color} stopOpacity={0.7} />
                <stop offset="100%" stopColor={link.target.color} stopOpacity={0.7} />
              </linearGradient>
            ))}
          </defs>

          {/* Links */}
          {layout.links.map((link, i) => {
            const sx = link.source.x1;
            const tx = link.target.x0;
            const sy = (link.y0 + link.y1) / 2;
            const ty = (link.y0 + link.y1) / 2;
            const mx = (sx + tx) / 2;
            const pathD = `M${sx},${sy} C${mx},${sy} ${mx},${ty} ${tx},${ty}`;

            const isHovered =
              hoveredLink === i ||
              hoveredNode === link.source.id ||
              hoveredNode === link.target.id;

            return (
              <path
                key={i}
                d={pathD}
                stroke={`url(#grad-${i})`}
                strokeWidth={Math.max(link.width, 2)}
                fill="none"
                strokeOpacity={isHovered ? 0.75 : 0.35}
                style={{ transition: 'stroke-opacity 0.15s', cursor: 'pointer' }}
                onMouseEnter={(e) => {
                  setHoveredLink(i);
                  setTooltip({
                    x: e.clientX,
                    y: e.clientY,
                    text: `${link.source.label} → ${link.target.label}: ${fmt.format(link.value)}`,
                  });
                }}
                onMouseMove={(e) => {
                  setTooltip((t) => (t ? { ...t, x: e.clientX, y: e.clientY } : null));
                }}
                onMouseLeave={() => {
                  setHoveredLink(null);
                  setTooltip(null);
                }}
              />
            );
          })}

          {/* Nodes */}
          {layout.nodes.map((node) => {
            const isHovered = hoveredNode === node.id;
            const isLeft = node.x0 < width / 2;
            const labelX = isLeft ? node.x1 + 6 : node.x0 - 6;
            const anchor = isLeft ? 'start' : 'end';
            const midY = (node.y0 + node.y1) / 2;
            const nodeHeight = Math.max(node.y1 - node.y0, 4);

            return (
              <g
                key={node.id}
                style={{ cursor: 'pointer' }}
                onMouseEnter={(e) => {
                  setHoveredNode(node.id);
                  const total = layout.links
                    .filter((l) => l.source.id === node.id || l.target.id === node.id)
                    .reduce((sum, l) => sum + l.value, 0);
                  setTooltip({
                    x: e.clientX,
                    y: e.clientY,
                    text: `${node.label}: ${fmt.format(total)}`,
                  });
                }}
                onMouseMove={(e) => {
                  setTooltip((t) => (t ? { ...t, x: e.clientX, y: e.clientY } : null));
                }}
                onMouseLeave={() => {
                  setHoveredNode(null);
                  setTooltip(null);
                }}
              >
                <rect
                  x={node.x0}
                  y={node.y0}
                  width={node.x1 - node.x0}
                  height={nodeHeight}
                  fill={node.color}
                  fillOpacity={isHovered ? 1 : 0.85}
                  rx={3}
                  style={{ transition: 'fill-opacity 0.15s' }}
                />
                <text
                  x={labelX}
                  y={midY}
                  dominantBaseline="middle"
                  textAnchor={anchor}
                  fontSize={11}
                  fill="#374151"
                  fontWeight={500}
                >
                  {node.label.length > 22 ? `${node.label.slice(0, 20)}…` : node.label}
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
          style={{ left: tooltip.x + 12, top: tooltip.y - 30 }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
