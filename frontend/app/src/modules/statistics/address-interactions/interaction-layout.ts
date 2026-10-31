import type { InteractionGraph } from './address-interaction-graph';
import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationLinkDatum, type SimulationNodeDatum } from 'd3-force';

export interface LayoutPoint {
  x: number;
  y: number;
}

interface LayoutNode extends SimulationNodeDatum {
  id: string;
}

interface LayoutLink extends SimulationLinkDatum<LayoutNode> {
  transactions: number;
}

/**
 * Ticks until alpha cools from 1 to about 0.01 under d3's default decay. The rest of the default
 * schedule (down to 0.001) costs another half again in time and only nudges nodes by a small
 * fraction of the layout's width.
 */
const TICKS = 200;

/** Leaves room for an avatar plus its label, so neighbours never sit on each other. */
const COLLIDE_RADIUS = 44;

/**
 * Positions for every address, computed once per graph.
 *
 * @remarks
 * The chart only draws these positions, so restyling for a selection never moves an address. The
 * layout is deterministic: d3-force seeds its own random source, so the same graph always lays out
 * the same way. Busier pairs sit a little closer. Weak centring forces keep separate clusters on
 * screen instead of drifting apart.
 */
export function layoutInteractionGraph(graph: InteractionGraph): Map<string, LayoutPoint> {
  const nodes: LayoutNode[] = graph.nodes.map(node => ({ id: node.id }));
  const links: LayoutLink[] = graph.connections.map(({ source, target, txCount }) => ({ source: source.id, target: target.id, transactions: txCount }));
  forceSimulation(nodes)
    .force('link', forceLink<LayoutNode, LayoutLink>(links)
      .id(node => node.id)
      .distance(link => 130 - Math.min(40, Math.log2(link.transactions) * 10)))
    .force('charge', forceManyBody<LayoutNode>().strength(-360).distanceMax(700))
    .force('collide', forceCollide<LayoutNode>(COLLIDE_RADIUS))
    .force('x', forceX<LayoutNode>(0).strength(0.06))
    .force('y', forceY<LayoutNode>(0).strength(0.06))
    .stop()
    .tick(TICKS);
  return new Map(nodes.map(node => [node.id, { x: node.x ?? 0, y: node.y ?? 0 }]));
}
