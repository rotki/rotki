<script setup lang="ts">
import type { LocationLabel } from '@/modules/core/common/location';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import LocationLabelSelector from '@/modules/history/LocationLabelSelector.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import { useChainColors } from './use-chain-colors';

const address = defineModel<string>('address', { required: true });
const chain = defineModel<string>('chain', { required: true });
const minTransactions = defineModel<number>('minTransactions', { required: true });

const { addressOptions, chains, maxTransactions, hasFilters = false } = defineProps<{
  addressOptions: LocationLabel[];
  chains: readonly string[];
  maxTransactions: number;
  /** Shows Reset filters at the end of the row while a chain or a minimum is set. */
  hasFilters?: boolean;
}>();

const emit = defineEmits<{
  reset: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();
const { chainColor } = useChainColors(() => chains);

const minTransactionsLabel = computed<string>(() => t('address_interactions.min_transactions', { count: get(minTransactions) }, get(minTransactions)));

function chipClass(selected: boolean): string {
  return selected
    ? 'border-rui-primary bg-rui-primary/10 text-rui-primary'
    : 'border-default text-rui-text-secondary hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800';
}
</script>

<template>
  <div class="flex flex-col gap-3 border-b border-default px-4 py-3">
    <div class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <LocationLabelSelector
        v-model="address"
        :options="addressOptions"
        :label="t('address_interactions.search')"
        variant="outlined"
        dense
        hide-details
        class="w-full sm:w-64"
        data-testid="interaction-search"
      />
      <RuiSlider
        v-if="maxTransactions > 1"
        v-model="minTransactions"
        :label="minTransactionsLabel"
        :min="1"
        :max="maxTransactions"
        :step="1"
        details="hidden"
        class="w-full sm:w-52"
        data-testid="interaction-min-transactions"
      />
      <RuiButton
        v-if="hasFilters"
        variant="text"
        color="primary"
        size="sm"
        class="ml-auto"
        data-testid="interaction-reset-filters"
        @click="emit('reset')"
      >
        {{ t('address_interactions.reset_filters') }}
      </RuiButton>
    </div>
    <div
      class="flex flex-wrap items-center gap-2"
      :aria-label="t('address_interactions.filter_chain')"
      role="group"
    >
      <button
        type="button"
        class="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-rui-primary"
        :class="chipClass(!chain)"
        :aria-pressed="!chain"
        data-testid="interaction-all-chains"
        @click="chain = ''"
      >
        {{ t('address_interactions.all_chains') }}
      </button>
      <button
        v-for="item in chains"
        :key="item"
        type="button"
        class="inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-rui-primary"
        :class="chipClass(chain === item)"
        :aria-pressed="chain === item"
        :data-chain="item"
        data-testid="interaction-chain"
        @click="chain = chain === item ? '' : item"
      >
        <span
          class="flex shrink-0 rounded-full"
          :style="{ boxShadow: `0 0 0 2px ${chainColor(item)}` }"
        >
          <LocationIcon
            :item="item"
            icon
            size="16px"
          />
        </span>
        {{ getChainName(item) }}
      </button>
    </div>
  </div>
</template>
