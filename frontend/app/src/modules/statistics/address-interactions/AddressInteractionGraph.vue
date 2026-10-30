<script setup lang="ts">
import type { AddressInteraction } from './address-interaction-types';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import LocationLabelSelector from '@/modules/history/LocationLabelSelector.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import AddressInteractionCanvas from './AddressInteractionCanvas.vue';
import AddressInteractionPanel from './AddressInteractionPanel.vue';
import { useAddressInteractionExplorer } from './use-address-interaction-explorer';

const { interactions } = defineProps<{ interactions: readonly AddressInteraction[] }>();
const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();
const {
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
  selectedConnectionId,
  selectedNode,
  selectedNodeId,
  selectNode,
  transactionCount,
} = useAddressInteractionExplorer(() => interactions);
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-default bg-rui-surface text-rui-text">
    <div class="flex flex-col gap-3 border-b border-default p-3 lg:px-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold">
            {{ t('address_interactions.graph_label') }}
          </h2>
          <p class="mt-1 text-sm text-rui-text-secondary">
            {{ t('address_interactions.graph_help') }}
          </p>
        </div>
        <LocationLabelSelector
          v-model="modelAddress"
          :options="addressOptions"
          :label="t('address_interactions.search')"
          variant="outlined"
          dense
          hide-details
          class="w-full sm:max-w-80"
          data-testid="interaction-search"
        />
      </div>
      <div
        class="flex flex-wrap items-center gap-2"
        :aria-label="t('address_interactions.filter_chain')"
        role="group"
      >
        <button
          type="button"
          class="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-rui-primary"
          :class="!modelChain ? 'border-rui-primary bg-rui-primary/10 text-rui-primary' : 'border-default text-rui-text-secondary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800'"
          :aria-pressed="!modelChain"
          data-testid="interaction-all-chains"
          @click="modelChain = ''"
        >
          {{ t('address_interactions.all_chains') }}
        </button>
        <button
          v-for="chain in chains"
          :key="chain"
          type="button"
          class="inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-rui-primary"
          :class="modelChain === chain ? 'border-rui-primary bg-rui-primary/10 text-rui-primary' : 'border-default text-rui-text-secondary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800'"
          :aria-pressed="modelChain === chain"
          :data-chain="chain"
          data-testid="interaction-chain"
          @click="modelChain = modelChain === chain ? '' : chain"
        >
          <LocationIcon
            :item="chain"
            icon
            size="16px"
          />
          {{ getChainName(chain) }}
        </button>
      </div>
    </div>
    <div class="grid xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div class="min-w-0">
        <div
          class="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-default px-4 py-2 text-sm text-rui-text-secondary"
          aria-live="polite"
        >
          <span>{{ t('address_interactions.addresses', { count: graph.nodes.length }) }}</span>
          <span>{{ t('address_interactions.connections', { count: connections.length }) }}</span>
          <span>{{ t('address_interactions.transactions', { count: transactionCount }) }}</span>
        </div>
        <AddressInteractionCanvas
          v-if="graph.nodes.length > 0"
          :graph="graph"
          :selected-node-id="selectedNodeId"
          :selected-connection-id="selectedConnectionId"
          @select-node="selectNode($event)"
          @select-connection="selectConnection($event)"
        />
        <div
          v-else
          class="flex h-[70dvh] min-h-120 flex-col items-center justify-center gap-3 p-8 text-center"
          data-testid="interaction-no-results"
        >
          <RuiIcon
            name="lu-search-x"
            size="32"
            class="text-rui-text-secondary"
          />
          <h3 class="font-medium">
            {{ t('address_interactions.no_results') }}
          </h3>
          <p class="max-w-80 text-sm text-rui-text-secondary">
            {{ t('address_interactions.no_results_hint') }}
          </p>
          <RuiButton
            variant="text"
            color="primary"
            data-testid="interaction-reset-filters"
            @click="resetFilters()"
          >
            {{ t('address_interactions.reset_filters') }}
          </RuiButton>
        </div>
        <div class="flex min-h-14 flex-wrap items-center justify-between gap-2 border-t border-default px-4 py-2">
          <span
            class="inline-flex items-center gap-1.5 text-xs text-rui-text-secondary"
            data-testid="interaction-decoded-hint"
          >
            <RuiIcon
              name="lu-info"
              size="14"
              class="shrink-0"
            />
            {{ t('address_interactions.decoded_events_hint') }}
          </span>
          <RuiButton
            v-if="selectedNode || selectedConnection"
            variant="text"
            color="primary"
            size="sm"
            data-testid="clear-interaction-selection"
            @click="clearSelection()"
          >
            {{ t('address_interactions.clear_selection') }}
          </RuiButton>
          <RuiButton
            v-else-if="hasFilters"
            variant="text"
            color="primary"
            size="sm"
            @click="resetFilters()"
          >
            {{ t('address_interactions.reset_filters') }}
          </RuiButton>
        </div>
      </div>
      <aside class="relative flex min-w-0 flex-col border-t border-default xl:border-t-0 xl:border-l">
        <div class="max-h-[70dvh] overflow-y-auto xl:absolute xl:inset-0 xl:max-h-none">
          <AddressInteractionPanel
            :connections="connections"
            :selected-node="selectedNode"
            :selected-connection="selectedConnection"
            :connection-label="connectionLabel"
            @select-connection="selectConnection($event)"
            @clear-connection="clearConnection()"
            @clear-node="clearSelection()"
          />
        </div>
      </aside>
    </div>
  </section>
</template>
