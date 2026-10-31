import { degreesOf, type InteractionConnection, type InteractionNode } from './address-interaction-graph';

/** Addresses that anyone reading the chain can tie together, directly or through each other. */
export interface InteractionCluster {
  nodeIds: string[];
  connections: InteractionConnection[];
  txCount: number;
  /** The best-connected address, which the cluster is named after. */
  lead: InteractionNode;
  /**
   * The connection with the fewest transactions among those whose removal splits the cluster.
   * `undefined` when every connection sits on a cycle, so no single one holds the cluster together.
   */
  weakestLink?: InteractionConnection;
}

export interface InteractionPath {
  /** Every address from start to end, in order. */
  nodes: InteractionNode[];
  connections: InteractionConnection[];
}

type Adjacency = Map<string, { neighbour: string; connection: InteractionConnection }[]>;

function nodesOf(connections: readonly InteractionConnection[]): Map<string, InteractionNode> {
  const nodes = new Map<string, InteractionNode>();
  for (const { source, target } of connections) {
    nodes.set(source.id, source);
    nodes.set(target.id, target);
  }
  return nodes;
}

function adjacencyOf(connections: readonly InteractionConnection[]): Adjacency {
  const adjacency: Adjacency = new Map();

  function link(from: string, neighbour: string, connection: InteractionConnection): void {
    const edges = adjacency.get(from);
    if (edges)
      edges.push({ connection, neighbour });
    else
      adjacency.set(from, [{ connection, neighbour }]);
  }
  for (const connection of connections) {
    link(connection.source.id, connection.target.id, connection);
    link(connection.target.id, connection.source.id, connection);
  }
  return adjacency;
}

interface SearchFrame {
  id: string;
  /** The connection this address was reached through; unset for the root of a search. */
  via?: string;
  next: number;
}

interface BridgeSearch {
  adjacency: Adjacency;
  order: Map<string, number>;
  low: Map<string, number>;
  bridges: Set<string>;
}

function discover(search: BridgeSearch, id: string): void {
  search.low.set(id, search.order.size);
  search.order.set(id, search.order.size);
}

/** Walks a frame's remaining connections, recording back edges, until one leads somewhere new. */
function nextChild(search: BridgeSearch, frame: SearchFrame): SearchFrame | undefined {
  const edges = search.adjacency.get(frame.id) ?? [];
  while (frame.next < edges.length) {
    const { connection, neighbour } = edges[frame.next++];
    if (connection.id === frame.via)
      continue;
    if (!search.order.has(neighbour)) {
      discover(search, neighbour);
      return { id: neighbour, next: 0, via: connection.id };
    }
    search.low.set(frame.id, Math.min(search.low.get(frame.id)!, search.order.get(neighbour)!));
  }
  return undefined;
}

/** Hands a finished address's lowest reachable order to its parent, and marks the way in as a bridge when nothing below it reaches back. */
function finish(search: BridgeSearch, frame: SearchFrame, parent: SearchFrame): void {
  if (!frame.via)
    return;
  search.low.set(parent.id, Math.min(search.low.get(parent.id)!, search.low.get(frame.id)!));
  if (search.low.get(frame.id)! > search.order.get(parent.id)!)
    search.bridges.add(frame.via);
}

/**
 * The connections whose removal disconnects the graph (Tarjan's bridge search).
 *
 * @remarks
 * The search keeps its own stack rather than recursing, so a long chain of addresses cannot
 * overflow the call stack. There is one connection per address pair, so skipping the connection an
 * address was reached through is enough to tell a back edge from the way in.
 */
function bridgesOf(adjacency: Adjacency): Set<string> {
  const search: BridgeSearch = { adjacency, bridges: new Set(), low: new Map(), order: new Map() };
  for (const root of adjacency.keys()) {
    if (search.order.has(root))
      continue;
    discover(search, root);
    const stack: SearchFrame[] = [{ id: root, next: 0 }];
    while (stack.length > 0) {
      const frame = stack.at(-1)!;
      const child = nextChild(search, frame);
      if (child) {
        stack.push(child);
        continue;
      }
      stack.pop();
      const parent = stack.at(-1);
      if (parent)
        finish(search, frame, parent);
    }
  }
  return search.bridges;
}

function componentFrom(start: string, adjacency: Adjacency, seen: Set<string>): string[] {
  const members = [start];
  seen.add(start);
  for (let index = 0; index < members.length; index++) {
    for (const { neighbour } of adjacency.get(members[index]) ?? []) {
      if (!seen.has(neighbour)) {
        seen.add(neighbour);
        members.push(neighbour);
      }
    }
  }
  return members.sort();
}

/** Fewer transactions is weaker; ties go to the lower id, so the pick never depends on order. */
function isWeaker(connection: InteractionConnection, than?: InteractionConnection): boolean {
  return !than || connection.txCount < than.txCount || (connection.txCount === than.txCount && connection.id < than.id);
}

/** The address with the most connections; ties go to the lowest id, since `nodeIds` is sorted. */
function busiestOf(cluster: InteractionCluster): string {
  const degrees = degreesOf(cluster.connections);
  return cluster.nodeIds.reduce((best, id) => (degrees.get(id) ?? 0) > (degrees.get(best) ?? 0) ? id : best);
}

/** Clusters of linked addresses, largest first, each with the link that holds it together most loosely. */
export function findClusters(connections: readonly InteractionConnection[]): InteractionCluster[] {
  const adjacency = adjacencyOf(connections);
  const bridges = bridgesOf(adjacency);
  const nodes = nodesOf(connections);
  const seen = new Set<string>();
  const clusterOf = new Map<string, InteractionCluster>();
  const clusters: InteractionCluster[] = [];
  for (const id of [...adjacency.keys()].sort()) {
    if (seen.has(id))
      continue;
    const nodeIds = componentFrom(id, adjacency, seen);
    const cluster: InteractionCluster = { connections: [], lead: nodes.get(nodeIds[0])!, nodeIds, txCount: 0 };
    for (const member of nodeIds)
      clusterOf.set(member, cluster);
    clusters.push(cluster);
  }
  for (const connection of connections) {
    const cluster = clusterOf.get(connection.source.id)!;
    cluster.connections.push(connection);
    cluster.txCount += connection.txCount;
    if (bridges.has(connection.id) && isWeaker(connection, cluster.weakestLink))
      cluster.weakestLink = connection;
  }
  for (const cluster of clusters)
    cluster.lead = nodes.get(busiestOf(cluster))!;
  return clusters.sort((a, b) => b.nodeIds.length - a.nodeIds.length || b.txCount - a.txCount);
}

/** The fewest connections that lead from one address to another, or `undefined` when they are not linked. */
export function findPath(from: string, to: string, connections: readonly InteractionConnection[]): InteractionPath | undefined {
  const adjacency = adjacencyOf(connections);
  const previous = new Map<string, { node: string; connection: InteractionConnection } | undefined>([[from, undefined]]);
  const queue = [from];
  for (let index = 0; index < queue.length && !previous.has(to); index++) {
    for (const { connection, neighbour } of adjacency.get(queue[index]) ?? []) {
      if (!previous.has(neighbour)) {
        previous.set(neighbour, { connection, node: queue[index] });
        queue.push(neighbour);
      }
    }
  }
  if (!previous.has(to) || from === to)
    return undefined;

  const nodes = nodesOf(connections);
  const nodeIds = [to];
  const steps: InteractionConnection[] = [];
  for (let step = previous.get(to); step; step = previous.get(step.node)) {
    steps.unshift(step.connection);
    nodeIds.unshift(step.node);
  }
  return { connections: steps, nodes: nodeIds.map(id => nodes.get(id)!) };
}
