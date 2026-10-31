import type { EChartsOption, GraphSeriesOption, TooltipComponentFormatterCallbackParams } from 'echarts';
import type { LayoutPoint } from './interaction-layout';
import type { InteractionIds, InteractionScene } from './interaction-scene';
import { degreesOf, type InteractionConnection, type InteractionNode } from './address-interaction-graph';

interface InteractionChartColors {
  /** A label's background: the surface, slightly see-through so lines stay visible under it. */
  labelSurface: string;
  /** The fill of a plain dot: a neutral that recedes behind the chain-coloured connections. */
  dot: string;
  muted: string;
  selection: string;
  surface: string;
  text: string;
}

/** What the chart needs from the scene alone, computed once per scene rather than per selection. */
export interface InteractionSceneMetrics {
  /** Active connections per address. */
  degrees: Map<string, number>;
  /** Addresses whose label always shows. */
  hubIds: Set<string>;
  /** Shrinks every node in a large graph, so fitting it on screen does not pile nodes on each other. */
  nodeScale: number;
  /** In a large graph, addresses outside the focus are plain dots: hundreds of tiny identicons read as noise. */
  plainDots: boolean;
}

export interface InteractionChartInput {
  scene: InteractionScene;
  metrics: InteractionSceneMetrics;
  focus?: InteractionIds;
  positions: ReadonlyMap<string, LayoutPoint>;
  /** Addresses drawn with a selection glow: the selected one, and a path's far end. */
  selectedNodeIds: ReadonlySet<string>;
  /** Connections drawn at full strength: the selected pair, or every step of a path. */
  highlightedConnectionIds: ReadonlySet<string>;
  /** Shared transactions that set a connection's width, after the chain filter. */
  weightOf: (connection: InteractionConnection) => number;
  connectionColor: (connection: InteractionConnection) => string;
  colors: InteractionChartColors;
  description: string;
  avatarOf: (node: InteractionNode) => string | undefined;
  nodeLabel: (node: InteractionNode) => string;
  /** Whether a node's label is a bare address, set in monospace like addresses elsewhere. */
  isBareAddress: (node: InteractionNode) => boolean;
  nodeTooltip: (node: InteractionNode) => string;
  connectionTooltip: (connection: InteractionConnection) => string;
}

type GraphNodeItem = NonNullable<GraphSeriesOption['data']>[number];

type GraphLinkItem = NonNullable<GraphSeriesOption['links']>[number];

type GraphNodeItemStyle = NonNullable<GraphSeriesOption['itemStyle']>;

const INACTIVE_NODE_OPACITY = 0.25;

const DIMMED_NODE_OPACITY = 0.2;

const EDGE_OPACITY = 0.6;

const INACTIVE_EDGE_OPACITY = 0.07;

const DIMMED_EDGE_OPACITY = 0.06;

/** Up to this many addresses, every label shows; past it only the busiest ones do, the rest on hover. */
const LABEL_ALL_LIMIT = 12;

const LABELLED_HUBS = 10;

/** Nodes grow with the number of active connections, so hubs stand out without dwarfing the rest. */
function nodeSize(degree: number): number {
  return 26 + Math.min(degree, 8) * 2;
}

/** Edges thicken logarithmically with shared transactions; one busy pair must not drown the graph. */
function edgeWidth(transactions: number): number {
  return 1.5 + Math.log2(Math.max(1, transactions));
}

/** Below this many addresses nodes keep their full size; past it they shrink with the square root of the count. */
const FULL_SIZE_NODES = 64;

/** Past this many addresses, only the selection and a small focus keep their identicons. */
const AVATAR_LIMIT = 60;

/** A plain dot is drawn smaller than an identicon, so the addresses that keep theirs stand out. */
const DOT_SCALE = 0.55;

/** Room below the graph for the legend overlaid in the canvas's bottom-left corner, so no node sits under it. */
const LEGEND_CLEARANCE = 120;

/** ECharts draws on a canvas, so the font is named directly instead of through a CSS class. */
const MONOSPACE = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';

export function sceneMetrics(scene: InteractionScene): InteractionSceneMetrics {
  const degrees = degreesOf(scene.connections.filter(({ id }) => scene.activeConnectionIds.has(id)));
  const hubIds = scene.nodes.length <= LABEL_ALL_LIMIT
    ? new Set(scene.nodes.map(node => node.id))
    : new Set([...scene.nodes]
        .sort((a, b) => (degrees.get(b.id) ?? 0) - (degrees.get(a.id) ?? 0))
        .slice(0, LABELLED_HUBS)
        .map(node => node.id));
  return {
    degrees,
    hubIds,
    nodeScale: Math.min(1, Math.sqrt(FULL_SIZE_NODES / Math.max(1, scene.nodes.length))),
    plainDots: scene.nodes.length > AVATAR_LIMIT,
  };
}

function nodeOpacity(input: InteractionChartInput, node: InteractionNode): number {
  if (!input.scene.activeNodeIds.has(node.id))
    return INACTIVE_NODE_OPACITY;
  if (input.focus && !input.focus.nodeIds.has(node.id))
    return DIMMED_NODE_OPACITY;
  return 1;
}

function linkOpacity(input: InteractionChartInput, connection: InteractionConnection): number {
  if (input.highlightedConnectionIds.has(connection.id))
    return 1;
  if (!input.scene.activeConnectionIds.has(connection.id))
    return INACTIVE_EDGE_OPACITY;
  if (input.focus && !input.focus.connectionIds.has(connection.id))
    return DIMMED_EDGE_OPACITY;
  return EDGE_OPACITY;
}

/**
 * Hubs always keep their label; everyone else only while in a small focus. A focused cluster of
 * dozens of addresses would otherwise pile its labels on top of each other.
 */
function isLabelled({ focus, metrics }: InteractionChartInput, node: InteractionNode): boolean {
  return metrics.hubIds.has(node.id) || isInSmallFocus(focus, node);
}

function isInSmallFocus(focus: InteractionIds | undefined, node: InteractionNode): boolean {
  return !!focus && focus.nodeIds.size <= LABEL_ALL_LIMIT && focus.nodeIds.has(node.id);
}

/** Whether an address is drawn as its identicon rather than a plain dot. */
function hasAvatar({ focus, metrics, selectedNodeIds }: InteractionChartInput, node: InteractionNode): boolean {
  return !metrics.plainDots || selectedNodeIds.has(node.id) || isInSmallFocus(focus, node);
}

function symbolSizeOf({ metrics }: InteractionChartInput, node: InteractionNode, selected: boolean, dot: boolean): number {
  const size = nodeSize(metrics.degrees.get(node.id) ?? 0) * metrics.nodeScale * (dot ? DOT_SCALE : 1);
  return size + (selected ? 8 : 0);
}

/** A plain dot is filled with the muted colour; an identicon sits on the surface with a muted ring. */
function nodeStyle(colors: InteractionChartColors, { dot, opacity, selected }: { dot: boolean; opacity: number; selected: boolean }): GraphNodeItemStyle {
  return {
    borderColor: dot ? colors.surface : colors.muted,
    borderWidth: dot ? 1 : 1.5,
    color: dot ? colors.dot : colors.surface,
    opacity,
    shadowBlur: selected ? 16 : 0,
    shadowColor: colors.selection,
  };
}

function nodeItem(input: InteractionChartInput, node: InteractionNode): GraphNodeItem {
  const { avatarOf, colors, positions, scene, selectedNodeIds } = input;
  const dot = !hasAvatar(input, node);
  const avatar = dot ? undefined : avatarOf(node);
  const position = positions.get(node.id);
  const opacity = nodeOpacity(input, node);
  const selected = selectedNodeIds.has(node.id);
  return {
    emphasis: { disabled: !scene.activeNodeIds.has(node.id) },
    id: node.id,
    itemStyle: nodeStyle(colors, { dot, opacity, selected }),
    label: { fontFamily: input.isBareAddress(node) ? MONOSPACE : undefined, opacity, show: isLabelled(input, node) },
    name: node.id,
    symbol: avatar ? `image://${avatar}` : 'circle',
    symbolSize: symbolSizeOf(input, node, selected, dot),
    x: position?.x ?? 0,
    y: position?.y ?? 0,
  };
}

function nodeItems(input: InteractionChartInput): GraphNodeItem[] {
  return input.scene.nodes.map(node => nodeItem(input, node));
}

function linkItems(input: InteractionChartInput): GraphLinkItem[] {
  const { colors, connectionColor, highlightedConnectionIds, scene, weightOf } = input;
  return scene.connections.map((connection) => {
    const highlighted = highlightedConnectionIds.has(connection.id);
    const active = scene.activeConnectionIds.has(connection.id);
    const weight = weightOf(connection);
    return {
      emphasis: { disabled: !active },
      lineStyle: {
        color: highlighted ? colors.selection : connectionColor(connection),
        opacity: linkOpacity(input, connection),
        width: edgeWidth(active ? weight : connection.txCount) + (highlighted ? 2 : 0),
      },
      source: connection.source.id,
      target: connection.target.id,
      value: weight,
    };
  });
}

/**
 * The ECharts option drawing the interaction graph from precomputed positions.
 *
 * @remarks
 * Nodes and links keep the order of `scene.nodes` and `scene.connections`, so a click's `dataIndex`
 * indexes those arrays. Positions come from {@link layoutInteractionGraph}, so restyling for a
 * filter or a selection never moves an address. The tooltip renders as rich text, so address-book
 * names never reach `innerHTML`.
 */
export function buildInteractionChartOption(input: InteractionChartInput): EChartsOption {
  const { colors, connectionTooltip, description, nodeLabel, nodeTooltip, scene } = input;
  const pill = {
    backgroundColor: colors.labelSurface,
    borderRadius: 3,
    color: colors.text,
  };

  function tooltip(params: TooltipComponentFormatterCallbackParams): string {
    const item = Array.isArray(params) ? params[0] : params;
    if (!item)
      return '';
    if (item.dataType === 'edge') {
      const connection = scene.connections[item.dataIndex];
      return connection ? connectionTooltip(connection) : '';
    }
    const node = scene.nodes[item.dataIndex];
    return node ? nodeTooltip(node) : '';
  }

  return {
    aria: { enabled: true, label: { description } },
    backgroundColor: 'transparent',
    series: [{
      bottom: LEGEND_CLEARANCE,
      data: nodeItems(input),
      emphasis: {
        focus: 'adjacency',
        label: { show: true },
        lineStyle: { opacity: 1 },
      },
      label: {
        ...pill,
        distance: 6,
        fontSize: 11,
        formatter: ({ dataIndex }): string => {
          const node = scene.nodes[dataIndex];
          return node ? nodeLabel(node) : '';
        },
        padding: [1, 4],
        position: 'bottom',
      },
      labelLayout: { hideOverlap: true },
      layout: 'none',
      left: 32,
      links: linkItems(input),
      preserveAspect: 'contain',
      right: 32,
      roam: true,
      scaleLimit: { max: 8, min: 0.2 },
      top: 32,
      type: 'graph',
    }],
    tooltip: {
      backgroundColor: colors.surface,
      borderColor: colors.muted,
      confine: true,
      formatter: tooltip,
      renderMode: 'richText',
      textStyle: { color: colors.text },
    },
  };
}
