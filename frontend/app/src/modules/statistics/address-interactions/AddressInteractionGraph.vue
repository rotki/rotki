<script setup lang="ts">
import type { AddressInteraction } from './address-interaction-types';
import AddressInteractionCanvas from './AddressInteractionCanvas.vue';
import AddressInteractionPanel from './AddressInteractionPanel.vue';
import AddressInteractionToolbar from './AddressInteractionToolbar.vue';
import { useAddressInteractionExplorer } from './use-address-interaction-explorer';
import { useInteractionLabels } from './use-interaction-labels';

/**
 * The address interactions card: filters, the graph and the side panel.
 *
 * @remarks
 * On wide screens the card fills the window below the page header, so the graph never scrolls off
 * and only the side panel scrolls. Its height subtracts 9.25rem: the app bar, the page's top and
 * bottom padding, and the header row with its gap. The page sets `scrollsItself`, so the shell adds
 * no room for the task dock; the side panel clears the dock through `--rotki-dock-inset` instead.
 */
const { interactions, loading = false } = defineProps<{
  interactions: readonly AddressInteraction[];
  /** A refresh is running: shown as a line along the card's top edge, so the card never moves. */
  loading?: boolean;
}>();
const { t } = useI18n({ useScope: 'global' });
const { shortAddressLabel } = useInteractionLabels();
const explorer = useAddressInteractionExplorer(() => interactions);
const {
  activeChain,
  addressOptions,
  cancelPath,
  chains,
  clearSelection,
  focus,
  graph,
  hasFilters,
  maxTransactions,
  modelAddress,
  modelChain,
  modelMinTransactions,
  pickingPath,
  resetFilters,
  scene,
  selectConnection,
  selectedNode,
  selection,
  selectNode,
  showHidden,
  stats,
} = explorer;
</script>

<template>
  <section
    class="relative flex flex-col overflow-hidden rounded-xl border border-default bg-rui-surface text-rui-text xl:h-[calc(100dvh-9.25rem)] xl:min-h-[36rem]"
    :aria-label="t('address_interactions.graph_label')"
  >
    <RuiProgress
      v-if="loading"
      variant="indeterminate"
      color="primary"
      class="absolute inset-x-0 top-0 z-10"
      :aria-label="t('address_interactions.loading')"
      data-testid="interaction-refreshing"
    />
    <AddressInteractionToolbar
      v-model:address="modelAddress"
      v-model:chain="modelChain"
      v-model:min-transactions="modelMinTransactions"
      :address-options="addressOptions"
      :chains="chains"
      :max-transactions="maxTransactions"
      :has-filters="hasFilters"
      @reset="resetFilters()"
    />
    <div class="grid min-h-0 flex-1 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div class="flex min-h-0 min-w-0 flex-col">
        <div
          v-if="pickingPath && selectedNode"
          class="flex flex-wrap items-center justify-between gap-2 border-b border-default bg-rui-primary/10 px-4 py-2 text-sm"
          data-testid="interaction-path-picking"
        >
          <span>{{ t('address_interactions.path.picking', { address: shortAddressLabel(selectedNode) }) }}</span>
          <RuiButton
            variant="outlined"
            color="primary"
            size="sm"
            @click="cancelPath()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
        </div>
        <div class="relative flex min-h-0 flex-1 flex-col">
          <AddressInteractionCanvas
            :graph="graph"
            :scene="scene"
            :focus="focus"
            :selection="selection"
            :chains="chains"
            :chain="activeChain"
            class="min-h-0 flex-1"
            @select-node="selectNode($event)"
            @select-connection="selectConnection($event)"
          >
            <template #summary>
              <div
                class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-rui-text-secondary"
                aria-live="polite"
                data-testid="interaction-stats"
              >
                <span>{{ t('address_interactions.stats.addresses', { count: stats.addresses }, stats.addresses) }}</span>
                <span>{{ t('address_interactions.stats.pairs', { count: stats.connections }, stats.connections) }}</span>
                <span>{{ t('address_interactions.tx_count', { count: stats.transactions }, stats.transactions) }}</span>
                <span>{{ t('address_interactions.stats.clusters', { count: stats.clusters }, stats.clusters) }}</span>
                <span
                  v-if="stats.muted > 0"
                  data-testid="interaction-muted"
                >
                  {{ t('address_interactions.stats.muted', { count: stats.muted }) }}
                </span>
                <RuiButton
                  v-if="stats.hidden > 0"
                  variant="text"
                  color="primary"
                  size="sm"
                  data-testid="interaction-show-hidden"
                  @click="showHidden()"
                >
                  {{ t('address_interactions.show_hidden', { count: stats.hidden }, stats.hidden) }}
                </RuiButton>
              </div>
            </template>
          </AddressInteractionCanvas>
          <div
            v-if="stats.connections === 0"
            class="pointer-events-none absolute inset-0 flex items-center justify-center p-4"
            data-testid="interaction-filtered-out"
          >
            <div class="pointer-events-auto flex flex-col items-center gap-2 rounded-lg border border-default bg-rui-surface px-5 py-4 text-center shadow-sm">
              <span class="text-sm font-medium">{{ t('address_interactions.filtered_out') }}</span>
              <RuiButton
                variant="outlined"
                color="primary"
                size="sm"
                @click="resetFilters()"
              >
                {{ t('address_interactions.reset_filters') }}
              </RuiButton>
            </div>
          </div>
        </div>
        <div class="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-default px-4 py-2">
          <div class="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-0.5 text-xs text-rui-text-secondary">
            <span>{{ t('address_interactions.canvas_hint') }}</span>
            <span
              class="inline-flex items-center gap-1.5"
              data-testid="interaction-decoded-hint"
            >
              <RuiIcon
                name="lu-info"
                size="14"
                class="shrink-0"
              />
              {{ t('address_interactions.decoded_events_hint') }}
            </span>
          </div>
          <RuiButton
            v-if="focus"
            variant="text"
            color="primary"
            size="sm"
            data-testid="clear-interaction-selection"
            @click="clearSelection()"
          >
            {{ t('address_interactions.clear_selection') }}
          </RuiButton>
        </div>
      </div>
      <aside class="min-h-0 min-w-0 border-t border-default pb-(--rotki-dock-inset) xl:overflow-y-auto xl:overscroll-contain xl:border-t-0 xl:border-l">
        <AddressInteractionPanel :explorer="explorer" />
      </aside>
    </div>
  </section>
</template>
