import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AddressInteraction } from './address-interaction-types';
import type { LocationLabel } from '@/modules/core/common/location';
import { isEqual } from 'es-toolkit';
import { type ChainActivity, createAddressInteractionGraph, type InteractionConnection, type InteractionGraph, type InteractionNode, touches, transactionsOn } from './address-interaction-graph';
import { sortByActivity } from './address-interaction-panel';
import { findClusters, findPath, type InteractionCluster, type InteractionPath } from './interaction-clusters';
import { activateScene, drawGraph, type DrawnGraph, focusOf, type InteractionIds, type InteractionScene } from './interaction-scene';
import { useInteractionLabels } from './use-interaction-labels';

interface InteractionStats {
  addresses: number;
  connections: number;
  transactions: number;
  clusters: number;
  muted: number;
  hidden: number;
}

export interface AddressInteractionExplorer {
  modelAddress: Ref<string>;
  modelChain: Ref<string>;
  /** The picked chain, or `undefined` for all chains. */
  activeChain: ComputedRef<string | undefined>;
  modelMinTransactions: Ref<number>;
  chains: ComputedRef<string[]>;
  maxTransactions: ComputedRef<number>;
  addressOptions: ComputedRef<LocationLabel[]>;
  graph: ComputedRef<InteractionGraph>;
  scene: ComputedRef<InteractionScene>;
  focus: ComputedRef<InteractionIds | undefined>;
  selection: ComputedRef<InteractionIds>;
  clusters: ComputedRef<InteractionCluster[]>;
  path: ComputedRef<InteractionPath | undefined>;
  connections: ComputedRef<InteractionConnection[]>;
  stats: ComputedRef<InteractionStats>;
  selectedNode: ComputedRef<InteractionNode | undefined>;
  selectedConnection: ComputedRef<InteractionConnection | undefined>;
  pathTarget: ComputedRef<InteractionNode | undefined>;
  selectedClusterIndex: ComputedRef<number | undefined>;
  pickingPath: Readonly<Ref<boolean>>;
  hasFilters: ComputedRef<boolean>;
  selectNode: (node: InteractionNode) => void;
  selectConnection: (connection: InteractionConnection) => void;
  selectCluster: (index: number) => void;
  startPath: () => void;
  cancelPath: () => void;
  clearPath: () => void;
  hideNode: (node: InteractionNode) => void;
  showHidden: () => void;
  clearConnection: () => void;
  clearSelection: () => void;
  resetFilters: () => void;
}

/** The slider's ceiling: past this many shared transactions, a pair counts as strongly linked anyway. */
const MAX_MIN_TRANSACTIONS = 20;

/** Two graphs are the same when every pair shares the same transactions on the same chains. */
function isSameGraph(a: InteractionGraph, b: InteractionGraph): boolean {
  const pairs = (graph: InteractionGraph): { id: string; activity: ChainActivity[] }[] => graph.connections.map(({ activity, id }) => ({ activity, id }));
  return a.nodes.length === b.nodes.length && isEqual(pairs(a), pairs(b));
}

/** Keeps the previous scene when a filter change activates exactly the same connections. */
function isSameScene(a: InteractionScene, b: InteractionScene): boolean {
  return a.connections === b.connections
    && a.activeConnectionIds.size === b.activeConnectionIds.size
    && [...a.activeConnectionIds].every(id => b.activeConnectionIds.has(id));
}

/**
 * Filter, selection and focus state of the address interactions page.
 *
 * @remarks
 * The graph is always built from every interaction, so its layout never changes while filtering.
 * Filters only decide which connections are active; the rest stay in place, greyed out. Searching
 * selects an address instead of filtering the graph down to it. Clusters and paths are worked out
 * on everything drawn, filters aside, because a single transaction is already enough to link two
 * addresses.
 */
export function useAddressInteractionExplorer(interactions: MaybeRefOrGetter<readonly AddressInteraction[]>): AddressInteractionExplorer {
  const { namedChain } = useInteractionLabels();
  const modelChain = shallowRef<string>('');
  const minTransactions = shallowRef<number>(1);
  const selectedNodeId = shallowRef<string>();
  const selectedConnectionId = shallowRef<string>();
  /** A cluster is remembered by one of its addresses, so re-sorting or growing clusters never moves the focus. */
  const selectedClusterKey = shallowRef<string>();
  const pathTargetId = shallowRef<string>();
  const pickingPath = shallowRef<boolean>(false);
  const hiddenIds = shallowRef<Set<string>>(new Set());

  /** A refresh returning the same rows keeps the previous array, so nothing downstream rebuilds. */
  const rows = computed<readonly AddressInteraction[]>((previous) => {
    const next = toValue(interactions);
    return previous && isEqual(previous, next) ? previous : next;
  });
  /** Rows that differ only in order still give the same graph, which then keeps the layout and view. */
  const graph = computed<InteractionGraph>((previous) => {
    const next = createAddressInteractionGraph(get(rows));
    return previous && isSameGraph(previous, next) ? previous : next;
  });
  const chains = computed<string[]>(() => [...new Set(get(graph).connections.flatMap(({ activity }) => activity.map(({ chain }) => chain)))].sort());
  const activeChain = computed<string | undefined>(() => get(modelChain) || undefined);
  const maxTransactions = computed<number>(() => Math.min(MAX_MIN_TRANSACTIONS, Math.max(1, ...get(graph).connections.map(({ txCount }) => txCount))));
  /** The chosen minimum, capped by what the data allows, so a smaller refresh never greys out everything. */
  const modelMinTransactions = computed<number>({
    get: () => Math.min(get(minTransactions), get(maxTransactions)),
    set: value => set(minTransactions, value),
  });
  const hasFilters = computed<boolean>(() => !!get(activeChain) || get(modelMinTransactions) > 1);
  const drawn = computed<DrawnGraph>(() => drawGraph(get(graph), get(hiddenIds)));
  const scene = computed<InteractionScene>((previous) => {
    const next = activateScene(get(drawn), { chain: get(activeChain), minTransactions: get(modelMinTransactions) });
    return previous && isSameScene(previous, next) ? previous : next;
  });
  const clusters = computed<InteractionCluster[]>(() => findClusters(get(drawn).connections));
  const selectedClusterIndex = computed<number | undefined>(() => {
    const key = get(selectedClusterKey);
    const index = get(clusters).findIndex(cluster => key !== undefined && cluster.nodeIds.includes(key));
    return index < 0 ? undefined : index;
  });

  const addressOptions = computed<LocationLabel[]>(() => get(drawn).nodes.map(node => ({
    location: namedChain(node),
    locationLabel: node.address,
  })));

  const nodesById = computed<Map<string, InteractionNode>>(() => new Map(get(drawn).nodes.map(node => [node.id, node])));
  const connectionsById = computed<Map<string, InteractionConnection>>(() => new Map(get(drawn).connections.map(connection => [connection.id, connection])));
  const selectedNode = computed<InteractionNode | undefined>(() => get(nodesById).get(get(selectedNodeId) ?? ''));
  const pathTarget = computed<InteractionNode | undefined>(() => get(nodesById).get(get(pathTargetId) ?? ''));
  const selectedConnection = computed<InteractionConnection | undefined>(() => get(connectionsById).get(get(selectedConnectionId) ?? ''));

  /** The search box shows the selected address, and picking one there selects it on the graph. */
  const modelAddress = computed<string>({
    get: () => get(selectedNode)?.id ?? '',
    set: (address) => {
      clearSelection();
      set(selectedNodeId, address || undefined);
    },
  });

  const path = computed<InteractionPath | undefined>(() => {
    const from = get(selectedNode)?.id;
    const to = get(pathTarget)?.id;
    return from && to ? findPath(from, to, get(drawn).connections) : undefined;
  });
  const focus = computed<InteractionIds | undefined>(() => focusOf(get(scene), {
    clusterNodeIds: get(clusters)[get(selectedClusterIndex) ?? -1]?.nodeIds,
    connection: get(selectedConnection),
    nodeId: get(selectedNode)?.id,
    path: get(path),
    pathTargetId: get(pathTarget)?.id,
  }));

  /** What is drawn as selected: the address, a path's far end, or both ends of a selected pair. */
  const selection = computed<InteractionIds>(() => {
    const pair = get(selectedConnection);
    const nodeIds = [get(selectedNode)?.id, get(pathTarget)?.id, pair?.source.id, pair?.target.id].filter(id => id !== undefined);
    const route = get(path);
    const connectionIds = route ? route.connections.map(({ id }) => id) : [pair?.id].filter(id => id !== undefined);
    return { connectionIds: new Set(connectionIds), nodeIds: new Set(nodeIds) };
  });

  /** Every active connection, busiest first; selecting an address only filters this, it never re-sorts. */
  const sortedConnections = computed<InteractionConnection[]>(() => {
    const { activeConnectionIds, connections: all } = get(scene);
    return sortByActivity(all.filter(connection => activeConnectionIds.has(connection.id)), get(activeChain));
  });
  /** The side list follows the graph: a selected address's connections, a focused cluster's, or all of them. */
  const connections = computed<InteractionConnection[]>(() => {
    const nodeId = get(selectedNode)?.id;
    if (nodeId)
      return get(sortedConnections).filter(connection => touches(connection, nodeId));
    const cluster = get(clusters)[get(selectedClusterIndex) ?? -1];
    if (cluster) {
      const members = new Set(cluster.nodeIds);
      return get(sortedConnections).filter(({ source }) => members.has(source.id));
    }
    return get(sortedConnections);
  });
  const stats = computed<InteractionStats>(() => {
    const active = get(sortedConnections);
    return {
      addresses: get(scene).activeNodeIds.size,
      clusters: get(clusters).length,
      connections: active.length,
      hidden: get(hiddenIds).size,
      muted: get(drawn).connections.length - active.length,
      transactions: active.reduce((sum, connection) => sum + transactionsOn(connection, get(activeChain)), 0),
    };
  });

  function clearSelection(): void {
    set(selectedNodeId, undefined);
    set(selectedConnectionId, undefined);
    set(selectedClusterKey, undefined);
    set(pathTargetId, undefined);
    set(pickingPath, false);
  }

  function selectNode(node: InteractionNode): void {
    const current = get(selectedNode)?.id;
    if (get(pickingPath) && current === node.id)
      return;
    if (get(pickingPath) && current) {
      set(pathTargetId, node.id);
      set(pickingPath, false);
      set(selectedConnectionId, undefined);
      return;
    }
    const next = current === node.id ? undefined : node.id;
    clearSelection();
    set(selectedNodeId, next);
  }

  /** Only an active connection can be selected; a greyed-out one is left alone. */
  function selectConnection(connection: InteractionConnection): void {
    if (!get(scene).activeConnectionIds.has(connection.id))
      return;
    const touchesNode = touches(connection, get(selectedNode)?.id);
    set(pathTargetId, undefined);
    set(pickingPath, false);
    set(selectedClusterKey, undefined);
    if (!touchesNode)
      set(selectedNodeId, undefined);
    set(selectedConnectionId, connection.id);
  }

  function selectCluster(index: number): void {
    const next = get(selectedClusterIndex) === index ? undefined : get(clusters)[index]?.nodeIds[0];
    clearSelection();
    set(selectedClusterKey, next);
  }

  function startPath(): void {
    set(pathTargetId, undefined);
    set(selectedConnectionId, undefined);
    set(pickingPath, true);
  }

  function cancelPath(): void {
    set(pickingPath, false);
  }

  function clearPath(): void {
    set(pathTargetId, undefined);
  }

  function hideNode(node: InteractionNode): void {
    clearSelection();
    set(hiddenIds, new Set([...get(hiddenIds), node.id]));
  }

  function showHidden(): void {
    set(hiddenIds, new Set());
  }

  function clearConnection(): void {
    set(selectedConnectionId, undefined);
  }

  function resetFilters(): void {
    set(modelChain, '');
    set(minTransactions, 1);
  }

  return {
    activeChain,
    addressOptions,
    cancelPath,
    chains,
    clearConnection,
    clearPath,
    clearSelection,
    clusters,
    connections,
    focus,
    graph,
    hasFilters,
    hideNode,
    maxTransactions,
    modelAddress,
    modelChain,
    modelMinTransactions,
    path,
    pathTarget,
    pickingPath: readonly(pickingPath),
    resetFilters,
    scene,
    selectCluster,
    selectConnection,
    selectedClusterIndex,
    selectedConnection,
    selectedNode,
    selection,
    selectNode,
    showHidden,
    startPath,
    stats,
  };
}
