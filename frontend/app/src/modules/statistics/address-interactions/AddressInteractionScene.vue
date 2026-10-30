<script setup lang="ts">
import type { InteractionConnection, InteractionGraph, InteractionNode } from './address-interaction-graph';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useScramble } from '@/modules/settings/use-scramble';
import { useInteractionRoutes } from './use-interaction-routes';

interface SceneNode {
  node: InteractionNode;
  description: string;
  label: string;
  chainLabel: string;
}

interface EdgeLabels {
  description: string;
  chainName: string;
}

/**
 * The edges and addresses of the interaction graph, in graph coordinates.
 *
 * @remarks
 * Kept apart from the pan and zoom state of `AddressInteractionCanvas`, so moving the view never
 * re-renders the graph. Each edge and node is memoized on what it displays, so a routing update or a
 * selection change only patches the elements it affects.
 */
const { graph, selectedNodeId, selectedConnectionId } = defineProps<{
  graph: InteractionGraph;
  selectedNodeId?: string;
  selectedConnectionId?: string;
}>();

const emit = defineEmits<{
  'select-node': [node: InteractionNode];
  'select-connection': [connection: InteractionConnection];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getAddressName } = useAddressNameResolution();
const { getChainName } = useSupportedChains();
const { scrambleAddress, scrambleData } = useScramble();

const routes = useInteractionRoutes(() => graph);

const relatedNodeIds = computed<Set<string>>(() => {
  const ids = new Set<string>();
  if (!selectedNodeId)
    return ids;

  ids.add(selectedNodeId);
  for (const connection of graph.connections) {
    if (connection.source.id === selectedNodeId || connection.target.id === selectedNodeId) {
      ids.add(connection.source.id);
      ids.add(connection.target.id);
    }
  }
  return ids;
});

function addressLabel(node: InteractionNode): string {
  if (!get(scrambleData)) {
    const name = node.chains.map(chain => getAddressName(node.address, chain)).find(Boolean);
    if (name)
      return name;
  }
  return scrambleAddress(node.address);
}

function shortLabel(node: InteractionNode, address: string): string {
  if (address === scrambleAddress(node.address))
    return truncateAddress(address, 6);
  const limit = 22;
  return address.length > limit ? `${address.slice(0, limit - 1)}…` : address;
}

const addressLabels = computed<Map<string, string>>(() => new Map(graph.nodes.map(node => [node.id, addressLabel(node)])));

const nodes = computed<SceneNode[]>(() => graph.nodes.map((node) => {
  const address = get(addressLabels).get(node.id)!;
  const chain = node.chains.map(getChainName).join(', ');
  return {
    node,
    description: t('address_interactions.select_address', { address, chain }),
    label: shortLabel(node, address),
    chainLabel: node.chains.length > 1 ? t('address_interactions.chain_count', { count: node.chains.length }) : chain,
  };
}));

const edgeLabels = computed<Map<string, EdgeLabels>>(() => new Map(graph.connections.map((connection) => {
  const chainName = getChainName(connection.chain);
  return [connection.id, {
    chainName,
    description: t('address_interactions.select_connection', {
      chain: chainName,
      source: get(addressLabels).get(connection.source.id)!,
      target: get(addressLabels).get(connection.target.id)!,
    }),
  }];
})));

function isRelated(connection: InteractionConnection): boolean {
  return !selectedNodeId || connection.source.id === selectedNodeId || connection.target.id === selectedNodeId;
}

/**
 * Stroke opacity of an edge's visible path.
 *
 * @remarks
 * Dims the stroke itself rather than the whole edge group, since group opacity makes the browser
 * composite every dimmed edge separately.
 */
function edgeOpacity(connection: InteractionConnection): number {
  const selected = selectedConnectionId === connection.id;
  if (isRelated(connection))
    return selected ? 1 : 0.45;
  return selected ? 0.2 : 0.09;
}
</script>

<template>
  <g
    v-for="route in routes"
    :key="route.connection.id"
    v-memo="[route, edgeLabels.get(route.connection.id), selectedConnectionId === route.connection.id, isRelated(route.connection)]"
    role="button"
    tabindex="0"
    :aria-label="edgeLabels.get(route.connection.id)?.description"
    :aria-pressed="selectedConnectionId === route.connection.id"
    :class="selectedConnectionId === route.connection.id ? 'text-rui-primary' : 'text-rui-text-secondary'"
    class="group cursor-pointer outline-offset-4 focus-visible:outline focus-visible:outline-rui-primary"
    data-testid="interaction-edge"
    @click="emit('select-connection', route.connection)"
    @keydown.enter.prevent="emit('select-connection', route.connection)"
    @keydown.space.prevent="emit('select-connection', route.connection)"
  >
    <title>{{ edgeLabels.get(route.connection.id)?.description }}</title>
    <path
      :d="route.path"
      fill="none"
      stroke="transparent"
      stroke-width="20"
    />
    <path
      :d="route.path"
      fill="none"
      stroke="currentColor"
      stroke-linejoin="round"
      :stroke-width="selectedConnectionId === route.connection.id ? 4 : 2"
      :stroke-opacity="edgeOpacity(route.connection)"
      class="group-hover:stroke-rui-primary group-focus-visible:stroke-rui-primary"
    />
    <text
      :x="route.labelX"
      :y="route.labelY - 5"
      :fill-opacity="isRelated(route.connection) ? 1 : 0.2"
      text-anchor="middle"
      class="fill-rui-text-secondary text-[10px]"
    >
      {{ edgeLabels.get(route.connection.id)?.chainName }}
    </text>
  </g>
  <g
    v-for="item in nodes"
    :key="item.node.id"
    v-memo="[item, selectedNodeId === item.node.id, !!selectedNodeId && !relatedNodeIds.has(item.node.id)]"
    :transform="`translate(${item.node.x}, ${item.node.y})`"
    role="button"
    tabindex="0"
    :aria-label="item.description"
    :aria-pressed="selectedNodeId === item.node.id"
    :class="{ 'opacity-25': selectedNodeId && !relatedNodeIds.has(item.node.id) }"
    class="group cursor-pointer text-rui-primary outline-offset-4 focus-visible:outline focus-visible:outline-rui-primary"
    data-testid="interaction-node"
    @click="emit('select-node', item.node)"
    @keydown.enter.prevent="emit('select-node', item.node)"
    @keydown.space.prevent="emit('select-node', item.node)"
  >
    <title>{{ item.description }}</title>
    <circle
      v-if="selectedNodeId === item.node.id"
      r="29"
      fill="currentColor"
      fill-opacity="0.15"
    />
    <circle
      r="21"
      class="fill-rui-surface group-hover:fill-rui-primary/10"
      stroke="currentColor"
      :stroke-width="selectedNodeId === item.node.id ? 3 : 1.5"
    />
    <path
      d="M-8-5h16v12H-8z M-8-5v-3H5v3 M3 0h5v4H3z"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linejoin="round"
      aria-hidden="true"
    />
    <text
      y="43"
      text-anchor="middle"
      class="fill-rui-text text-[13px] font-medium"
    >
      {{ item.label }}
    </text>
    <text
      y="61"
      text-anchor="middle"
      class="fill-rui-text-secondary text-xs"
    >
      {{ item.chainLabel }}
    </text>
  </g>
</template>
