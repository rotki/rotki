<script setup lang="ts">
import type { InteractionConnection, InteractionGraph, InteractionNode } from './address-interaction-graph';
import AddressInteractionScene from './AddressInteractionScene.vue';
import { useInteractionViewport } from './use-interaction-viewport';

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
          <AddressInteractionScene
            :graph="graph"
            :selected-node-id="selectedNodeId"
            :selected-connection-id="selectedConnectionId"
            @select-node="emit('select-node', $event)"
            @select-connection="emit('select-connection', $event)"
          />
        </g>
      </svg>
    </div>
  </div>
</template>
