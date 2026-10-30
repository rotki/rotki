<script setup lang="ts">
import type { InteractionConnection, InteractionGraph, InteractionNode } from './address-interaction-graph';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useScramble } from '@/modules/settings/use-scramble';
import { routeInteractionEdge } from './interaction-edge-routing';
import { useInteractionViewport } from './use-interaction-viewport';

interface CanvasNode {
  node: InteractionNode;
  address: string;
  chain: string;
  label: string;
  x: number;
  y: number;
}

interface CanvasConnection {
  connection: InteractionConnection;
  path: string;
  labelX: number;
  labelY: number;
}

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

const nodes = computed<CanvasNode[]>(() => graph.nodes.map((node) => {
  const address = addressLabel(node);
  return {
    node,
    address,
    chain: node.chains.map(getChainName).join(', '),
    label: shortLabel(node, address),
    x: node.x,
    y: node.y,
  };
}));

const connections = computed<CanvasConnection[]>(() => {
  const pairs = new Map<string, InteractionConnection[]>();
  for (const connection of graph.connections) {
    const key = JSON.stringify([connection.source.id, connection.target.id]);
    const pair = pairs.get(key) ?? [];
    pair.push(connection);
    pairs.set(key, pair);
  }
  return [...pairs.values()].flatMap(pair => pair.map((connection, index) => ({
    connection,
    ...routeInteractionEdge(connection.source, connection.target, graph.nodes, index, pair.length),
  })));
});

function isRelated(connection: InteractionConnection): boolean {
  return !selectedNodeId || connection.source.id === selectedNodeId || connection.target.id === selectedNodeId;
}

function connectionLabel(connection: InteractionConnection): string {
  return t('address_interactions.select_connection', {
    chain: getChainName(connection.chain),
    source: addressLabel(connection.source),
    target: addressLabel(connection.target),
  });
}

const viewport = useTemplateRef<HTMLDivElement>('viewport');
const bounds = computed<{ width: number; height: number }>(() => ({
  width: Math.max(240, ...graph.nodes.map(node => node.x + 110)),
  height: Math.max(160, ...graph.nodes.map(node => node.y + 90)),
}));
const {
  changeZoom,
  dragging,
  fitGraph,
  height: viewportHeight,
  modelZoom: zoom,
  onClick,
  onKeydown,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onWheel,
  transform,
  width: viewportWidth,
} = useInteractionViewport(bounds, viewport);
</script>

<template>
  <div class="min-w-0 bg-rui-grey-50 dark:bg-rui-grey-900">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-default px-3 py-1.5">
      <p class="min-w-48 flex-1 text-xs leading-5 text-rui-text-secondary">
        {{ t('address_interactions.canvas_hint') }}
      </p>
      <div class="ml-auto flex shrink-0 items-center gap-1">
        <RuiButton
          variant="text"
          icon
          size="sm"
          :disabled="zoom === 0.25"
          :aria-label="t('address_interactions.zoom_out')"
          data-testid="interaction-zoom-out"
          @click="changeZoom(-0.25)"
        >
          <RuiIcon
            name="lu-minus"
            size="18"
            aria-hidden="true"
          />
        </RuiButton>
        <span
          class="w-12 text-center text-xs tabular-nums text-rui-text-secondary"
          aria-live="polite"
        >
          {{ t('address_interactions.zoom_level', { percent: Math.round(zoom * 100) }) }}
        </span>
        <RuiButton
          variant="text"
          icon
          size="sm"
          :disabled="zoom === 8"
          :aria-label="t('address_interactions.zoom_in')"
          data-testid="interaction-zoom-in"
          @click="changeZoom(0.25)"
        >
          <RuiIcon
            name="lu-plus"
            size="18"
            aria-hidden="true"
          />
        </RuiButton>
        <RuiButton
          variant="text"
          size="sm"
          data-testid="interaction-fit-graph"
          @click="fitGraph()"
        >
          {{ t('address_interactions.fit_graph') }}
        </RuiButton>
      </div>
    </div>
    <div
      ref="viewport"
      class="h-[70dvh] min-h-120 touch-none overflow-hidden overscroll-contain select-none focus-visible:outline focus-visible:outline-rui-primary"
      :class="dragging ? 'cursor-grabbing' : 'cursor-grab'"
      :aria-label="t('address_interactions.graph_label')"
      role="region"
      tabindex="0"
      data-testid="interaction-canvas-viewport"
      @wheel.prevent="onWheel($event)"
      @pointerdown="onPointerDown($event)"
      @pointermove="onPointerMove($event)"
      @pointerup="onPointerUp()"
      @pointercancel="onPointerUp()"
      @lostpointercapture="onPointerUp()"
      @click.capture="onClick($event)"
      @keydown="onKeydown($event)"
    >
      <svg
        :viewBox="`0 0 ${viewportWidth} ${viewportHeight}`"
        width="100%"
        height="100%"
        :aria-label="t('address_interactions.graph_label')"
        role="group"
        class="block max-w-none"
        data-testid="address-interaction-network"
      >
        <g
          :transform="transform"
          data-testid="interaction-canvas-transform"
        >
          <g
            v-for="{ connection, path, labelX, labelY } in connections"
            :key="connection.id"
            role="button"
            tabindex="0"
            :aria-label="connectionLabel(connection)"
            :aria-pressed="selectedConnectionId === connection.id"
            :class="[
              selectedConnectionId === connection.id ? 'text-rui-primary' : 'text-rui-text-secondary',
              { 'opacity-20': !isRelated(connection) },
            ]"
            class="group cursor-pointer outline-offset-4 focus-visible:outline focus-visible:outline-rui-primary"
            data-testid="interaction-edge"
            @click="emit('select-connection', connection)"
            @keydown.enter.prevent="emit('select-connection', connection)"
            @keydown.space.prevent="emit('select-connection', connection)"
          >
            <title>{{ connectionLabel(connection) }}</title>
            <path
              :d="path"
              fill="none"
              stroke="transparent"
              stroke-width="20"
            />
            <path
              :d="path"
              fill="none"
              stroke="currentColor"
              stroke-linejoin="round"
              :stroke-width="selectedConnectionId === connection.id ? 4 : 2"
              :stroke-opacity="selectedConnectionId === connection.id ? 1 : 0.45"
              class="group-hover:stroke-rui-primary group-focus-visible:stroke-rui-primary"
            />
            <text
              :x="labelX"
              :y="labelY - 5"
              text-anchor="middle"
              class="fill-rui-text-secondary text-[10px]"
            >
              {{ getChainName(connection.chain) }}
            </text>
          </g>
          <g
            v-for="{ node, address, chain, label, x, y } in nodes"
            :key="node.id"
            :transform="`translate(${x}, ${y})`"
            role="button"
            tabindex="0"
            :aria-label="t('address_interactions.select_address', { address, chain })"
            :aria-pressed="selectedNodeId === node.id"
            :class="{ 'opacity-25': selectedNodeId && !relatedNodeIds.has(node.id) }"
            class="group cursor-pointer text-rui-primary outline-offset-4 focus-visible:outline focus-visible:outline-rui-primary"
            data-testid="interaction-node"
            @click="emit('select-node', node)"
            @keydown.enter.prevent="emit('select-node', node)"
            @keydown.space.prevent="emit('select-node', node)"
          >
            <title>{{ t('address_interactions.select_address', { address, chain }) }}</title>
            <circle
              v-if="selectedNodeId === node.id"
              r="29"
              fill="currentColor"
              fill-opacity="0.15"
            />
            <circle
              r="21"
              class="fill-rui-surface group-hover:fill-rui-primary/10"
              stroke="currentColor"
              :stroke-width="selectedNodeId === node.id ? 3 : 1.5"
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
              {{ label }}
            </text>
            <text
              y="61"
              text-anchor="middle"
              class="fill-rui-text-secondary text-xs"
            >
              {{ node.chains.length > 1 ? t('address_interactions.chain_count', { count: node.chains.length }) : chain }}
            </text>
          </g>
        </g>
      </svg>
    </div>
  </div>
</template>
