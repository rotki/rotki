import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AddressInteraction } from './address-interaction-types';
import type { LocationLabel } from '@/modules/core/common/location';
import { useScramble } from '@/modules/settings/use-scramble';
import { createAddressInteractionGraph, type InteractionConnection, type InteractionGraph, type InteractionNode } from './address-interaction-graph';
import { sortByActivity, useNamedChain } from './address-interaction-panel';

interface UseAddressInteractionExplorerReturn {
  modelAddress: Ref<string>;
  modelChain: Ref<string>;
  chains: ComputedRef<string[]>;
  addressOptions: ComputedRef<LocationLabel[]>;
  graph: ComputedRef<InteractionGraph>;
  connections: ComputedRef<InteractionConnection[]>;
  selectedNode: ComputedRef<InteractionNode | undefined>;
  selectedConnection: ComputedRef<InteractionConnection | undefined>;
  selectedNodeId: Readonly<Ref<string | undefined>>;
  selectedConnectionId: Readonly<Ref<string | undefined>>;
  transactionCount: ComputedRef<number>;
  hasFilters: ComputedRef<boolean>;
  connectionLabel: (connection: InteractionConnection) => string;
  selectNode: (node: InteractionNode) => void;
  selectConnection: (connection: InteractionConnection) => void;
  clearConnection: () => void;
  clearSelection: () => void;
  resetFilters: () => void;
}

export function useAddressInteractionExplorer(interactions: MaybeRefOrGetter<readonly AddressInteraction[]>): UseAddressInteractionExplorerReturn {
  const { t } = useI18n({ useScope: 'global' });
  const namedChain = useNamedChain();
  const { scrambleAddress } = useScramble();
  const modelAddress = shallowRef<string>('');
  const modelChain = shallowRef<string>('');
  const selectedNodeId = shallowRef<string>();
  const selectedConnectionId = shallowRef<string>();
  const chains = computed<string[]>(() => [...new Set(toValue(interactions).map(entry => entry.chain))].sort());
  const hasFilters = computed<boolean>(() => !!get(modelAddress) || !!get(modelChain));
  const chainInteractions = computed<readonly AddressInteraction[]>(() => toValue(interactions).filter(entry =>
    !get(modelChain) || entry.chain === get(modelChain)));
  const filteredInteractions = computed<readonly AddressInteraction[]>(() => {
    const address = get(modelAddress);
    return address
      ? get(chainInteractions).filter(entry => entry.source === address || entry.target === address)
      : get(chainInteractions);
  });
  const addressOptions = computed<LocationLabel[]>(() => {
    const chainsByAddress = new Map<string, string[]>();
    for (const { chain, source, target } of get(chainInteractions)) {
      for (const address of [source, target]) {
        const known = chainsByAddress.get(address) ?? [];
        if (!known.includes(chain))
          chainsByAddress.set(address, [...known, chain].sort());
      }
    }
    return [...chainsByAddress].sort(([a], [b]) => a.localeCompare(b)).map(([address, addressChains]) => ({
      location: namedChain(address, addressChains),
      locationLabel: address,
    }));
  });
  const graph = computed<InteractionGraph>(() => createAddressInteractionGraph(get(filteredInteractions)));
  const selectedNode = computed<InteractionNode | undefined>(() => get(graph).nodes.find(node => node.id === get(selectedNodeId)));
  const selectedConnection = computed<InteractionConnection | undefined>(() => get(graph).connections.find(connection => connection.id === get(selectedConnectionId)));
  const connections = computed<InteractionConnection[]>(() => sortByActivity(get(graph).connections.filter(isRelated)));
  const transactionCount = computed<number>(() => new Set(get(connections).flatMap(connection =>
    connection.txHashes.map(hash => JSON.stringify([connection.chain, hash])),
  )).size);

  function connectionLabel(connection: InteractionConnection): string {
    return t('address_interactions.select_connection', {
      chain: connection.chain,
      source: scrambleAddress(connection.source.address),
      target: scrambleAddress(connection.target.address),
    });
  }

  function isRelated(connection: InteractionConnection): boolean {
    const id = get(selectedNodeId);
    return !id || connection.source.id === id || connection.target.id === id;
  }

  function selectNode(node: InteractionNode): void {
    set(selectedNodeId, get(selectedNodeId) === node.id ? undefined : node.id);
    set(selectedConnectionId, undefined);
  }

  function selectConnection(connection: InteractionConnection): void {
    if (!isRelated(connection))
      set(selectedNodeId, undefined);
    set(selectedConnectionId, connection.id);
  }

  function clearConnection(): void {
    set(selectedConnectionId, undefined);
  }

  function clearSelection(): void {
    set(modelAddress, '');
    set(selectedNodeId, undefined);
    set(selectedConnectionId, undefined);
  }

  function resetFilters(): void {
    set(modelChain, '');
    clearSelection();
  }

  watch(modelAddress, (address) => {
    set(selectedNodeId, address || undefined);
    set(selectedConnectionId, undefined);
  });

  watch(graph, (value) => {
    if (!value.nodes.some(node => node.id === get(selectedNodeId)))
      set(selectedNodeId, undefined);
    if (!value.connections.some(connection => connection.id === get(selectedConnectionId)))
      set(selectedConnectionId, undefined);
  });

  return {
    addressOptions,
    chains,
    clearConnection,
    clearSelection,
    connectionLabel,
    connections,
    graph,
    hasFilters,
    modelAddress,
    modelChain,
    resetFilters,
    selectConnection,
    selectedConnection,
    selectedConnectionId: readonly(selectedConnectionId),
    selectedNode,
    selectedNodeId: readonly(selectedNodeId),
    selectNode,
    transactionCount,
  };
}
