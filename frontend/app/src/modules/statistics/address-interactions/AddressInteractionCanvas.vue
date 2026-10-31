<script setup lang="ts">
import type { ECElementEvent, EChartsOption } from 'echarts';
import type { InteractionIds, InteractionScene } from './interaction-scene';
import VChart from 'vue-echarts';
import { useScramble } from '@/modules/settings/use-scramble';
import { useGraph } from '@/modules/statistics/use-graph';
import { type InteractionConnection, type InteractionGraph, type InteractionNode, transactionsOn } from './address-interaction-graph';
import { buildInteractionChartOption, type InteractionSceneMetrics, sceneMetrics } from './interaction-chart-option';
import { layoutInteractionGraph, type LayoutPoint } from './interaction-layout';
import { useChainColors } from './use-chain-colors';
import { useInteractionLabels } from './use-interaction-labels';
import { useNodeAvatars } from './use-node-avatars';

/**
 * The interaction graph, drawn by ECharts at positions laid out once per graph.
 *
 * @remarks
 * `graph` holds every address, so its layout ignores filters; `scene` says what is drawn and what
 * is active. Pan and zoom only reset when `graph` changes or the user asks to fit the graph.
 */
const { graph, scene, focus, selection, chains, chain } = defineProps<{
  graph: InteractionGraph;
  scene: InteractionScene;
  focus?: InteractionIds;
  selection: InteractionIds;
  chains: readonly string[];
  chain?: string;
}>();

const emit = defineEmits<{
  'select-node': [node: InteractionNode];
  'select-connection': [connection: InteractionConnection];
}>();

defineSlots<{
  /** Rendered at the start of the header row, before the fit-graph button: the page puts its counts here. */
  summary?: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const viewKey = ref<number>(0);

const { isDark } = useRotkiTheme();
const { baseColor, secondaryColor } = useGraph();
const { scrambleAddress } = useScramble();
const { chartLabel, connectionTooltip, hasName, nodeTooltip } = useInteractionLabels();
const { connectionColor, neutral } = useChainColors(() => chains);

const surface = computed<string>(() => get(isDark) ? '#18181b' : '#fafafa');
const positions = computed<Map<string, LayoutPoint>>(() => layoutInteractionGraph(graph));
const avatars = useNodeAvatars(() => graph.nodes.map(node => scrambleAddress(node.address)), surface);

const metrics = computed<InteractionSceneMetrics>(() => sceneMetrics(scene));

/**
 * The chart option, marked raw because vue-echarts deep-watches it: a graph's worth of node and
 * link objects is too much to traverse on every rebuild, and the option is replaced, never mutated.
 */
const option = computed<EChartsOption>(() => markRaw(buildInteractionChartOption({
  avatarOf: node => get(avatars).get(scrambleAddress(node.address)),
  colors: {
    dot: get(neutral),
    muted: get(secondaryColor),
    selection: get(baseColor),
    labelSurface: get(isDark) ? 'rgba(24, 24, 27, 0.72)' : 'rgba(250, 250, 250, 0.72)',
    surface: get(surface),
    text: get(isDark) ? 'rgba(255, 255, 255, 0.87)' : 'rgba(0, 0, 0, 0.87)',
  },
  connectionColor: connection => connectionColor(connection, chain),
  connectionTooltip,
  description: t('address_interactions.graph_help'),
  focus,
  highlightedConnectionIds: selection.connectionIds,
  isBareAddress: node => !hasName(node),
  metrics: get(metrics),
  nodeLabel: chartLabel,
  nodeTooltip,
  positions: get(positions),
  scene,
  selectedNodeIds: selection.nodeIds,
  weightOf: connection => transactionsOn(connection, chain),
})));

function onClick(event: ECElementEvent): void {
  if (event.dataType === 'edge') {
    const connection = scene.connections[event.dataIndex];
    if (connection)
      emit('select-connection', connection);
  }
  else if (event.dataType === 'node') {
    const node = scene.nodes[event.dataIndex];
    if (node)
      emit('select-node', node);
  }
}

/** Remounting the chart drops its pan and zoom, so the whole graph is back in view. */
function fitGraph(): void {
  set(viewKey, get(viewKey) + 1);
}

watch(() => graph, fitGraph);
</script>

<template>
  <div class="relative flex min-w-0 flex-col bg-rui-grey-50 dark:bg-rui-grey-900">
    <div class="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-1 border-b border-default px-4 py-1.5">
      <div class="mr-auto">
        <slot name="summary" />
      </div>
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="-mr-2"
        :aria-label="t('address_interactions.fit_graph')"
        :title="t('address_interactions.fit_graph')"
        data-testid="interaction-fit-graph"
        @click="fitGraph()"
      >
        <RuiIcon
          name="lu-maximize"
          size="16"
        />
      </RuiButton>
    </div>
    <VChart
      :key="viewKey"
      :option="option"
      :aria-label="t('address_interactions.graph_label')"
      autoresize
      class="h-[60dvh]! min-h-96 xl:h-auto! xl:min-h-0 xl:flex-1"
      data-testid="address-interaction-network"
      @click="onClick($event)"
    />
    <ul
      class="pointer-events-none absolute bottom-3 left-3 flex flex-col gap-1 rounded-md border border-default bg-rui-surface/90 px-2.5 py-2 text-xs text-rui-text-secondary"
      :aria-label="t('address_interactions.legend.title')"
      data-testid="interaction-legend"
    >
      <li class="flex items-center gap-1.5">
        <span
          class="h-0.5 w-6 rounded-full bg-rui-grey-500"
          aria-hidden="true"
        />
        {{ t('address_interactions.legend.few') }}
      </li>
      <li class="flex items-center gap-1.5">
        <span
          class="h-1.5 w-6 rounded-full bg-rui-grey-500"
          aria-hidden="true"
        />
        {{ t('address_interactions.legend.many') }}
      </li>
      <li
        v-if="!chain"
        class="flex items-center gap-1.5"
      >
        <span
          class="h-1 w-6 rounded-full"
          :style="{ backgroundColor: neutral }"
          aria-hidden="true"
        />
        {{ t('address_interactions.legend.several_chains') }}
      </li>
    </ul>
  </div>
</template>
