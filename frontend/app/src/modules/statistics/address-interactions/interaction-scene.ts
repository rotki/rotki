import type { InteractionPath } from './interaction-clusters';
import { type InteractionConnection, type InteractionGraph, type InteractionNode, touches, transactionsOn } from './address-interaction-graph';

export interface InteractionFilters {
  chain?: string;
  minTransactions: number;
}

/** The addresses and connections the graph draws: everything but hidden addresses. */
export interface DrawnGraph {
  nodes: InteractionNode[];
  connections: InteractionConnection[];
}

/** What the graph draws, and which of it passes the filters. Filtered items stay in place, greyed out. */
export interface InteractionScene extends DrawnGraph {
  activeConnectionIds: Set<string>;
  activeNodeIds: Set<string>;
}

/**
 * A set of addresses and the connections between them: what a selection is about (the focus), or
 * what is drawn as selected.
 */
export interface InteractionIds {
  nodeIds: ReadonlySet<string>;
  connectionIds: ReadonlySet<string>;
}

interface FocusSelection {
  nodeId?: string;
  connection?: InteractionConnection;
  clusterNodeIds?: readonly string[];
  path?: InteractionPath;
  pathTargetId?: string;
}

/** Leaves out hidden addresses and every connection touching one. */
export function drawGraph(graph: InteractionGraph, hiddenIds: ReadonlySet<string>): DrawnGraph {
  if (hiddenIds.size === 0)
    return { connections: graph.connections, nodes: graph.nodes };
  return {
    connections: graph.connections.filter(({ source, target }) => !hiddenIds.has(source.id) && !hiddenIds.has(target.id)),
    nodes: graph.nodes.filter(node => !hiddenIds.has(node.id)),
  };
}

/**
 * Marks which drawn connections and addresses pass the chain and minimum-transactions filters.
 *
 * @remarks
 * A connection on another chain, or with fewer transactions than the minimum, stays drawn but
 * inactive, so changing a filter never moves the layout. The drawn arrays are passed through
 * unchanged, so anything derived from them alone survives a filter change.
 */
export function activateScene(drawn: DrawnGraph, { chain, minTransactions }: InteractionFilters): InteractionScene {
  const { connections, nodes } = drawn;
  const activeConnectionIds = new Set<string>();
  const activeNodeIds = new Set<string>();
  for (const connection of connections) {
    const transactions = transactionsOn(connection, chain);
    if (transactions > 0 && transactions >= minTransactions) {
      activeConnectionIds.add(connection.id);
      activeNodeIds.add(connection.source.id);
      activeNodeIds.add(connection.target.id);
    }
  }
  return { activeConnectionIds, activeNodeIds, connections, nodes };
}

function neighbourhoodOf(scene: InteractionScene, nodeId: string): InteractionIds {
  const nodeIds = new Set<string>([nodeId]);
  const connectionIds = new Set<string>();
  for (const connection of scene.connections) {
    const { source, target } = connection;
    if (scene.activeConnectionIds.has(connection.id) && touches(connection, nodeId)) {
      connectionIds.add(connection.id);
      nodeIds.add(source.id);
      nodeIds.add(target.id);
    }
  }
  return { connectionIds, nodeIds };
}

/**
 * The part of the graph the current selection is about; everything else is dimmed.
 *
 * @returns `undefined` when nothing is selected, so nothing is dimmed.
 */
export function focusOf(scene: InteractionScene, selection: FocusSelection): InteractionIds | undefined {
  const { clusterNodeIds, connection, nodeId, path, pathTargetId } = selection;
  if (nodeId && pathTargetId) {
    if (!path)
      return { connectionIds: new Set(), nodeIds: new Set([nodeId, pathTargetId]) };
    return { connectionIds: new Set(path.connections.map(({ id }) => id)), nodeIds: new Set(path.nodes.map(({ id }) => id)) };
  }
  if (connection)
    return { connectionIds: new Set([connection.id]), nodeIds: new Set([connection.source.id, connection.target.id]) };
  if (nodeId)
    return neighbourhoodOf(scene, nodeId);
  if (clusterNodeIds) {
    const nodeIds = new Set(clusterNodeIds);
    const connectionIds = new Set(scene.connections
      .filter(({ source, target }) => nodeIds.has(source.id) && nodeIds.has(target.id))
      .map(({ id }) => id));
    return { connectionIds, nodeIds };
  }
  return undefined;
}
