<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useLocationBalanceStatus } from '@/modules/balances/use-location-balance-status';
import { bigNumberSum } from '@/modules/core/common/data/calculation';

const { identifier } = defineProps<{ identifier: string }>();

const { t } = useI18n({ useScope: 'global' });

const { useLocationBreakdown } = useAggregatedBalances();
const breakdown = useLocationBreakdown(() => identifier);

/**
 * Summed from the breakdown, so the tile always agrees with the table beneath it. Reading
 * `balancesByLocation` instead would undercount, since it exposes no chain-aliased key and so
 * misses a manual balance tagged with that alias.
 */
const totalValue = computed<BigNumber>(() => bigNumberSum(get(breakdown).map(entry => entry.value)));

const { isInitialLoading } = useLocationBalanceStatus(identifier);

/** Only while there is nothing to show; a refresh keeps the last figures in place. */
const showSkeleton = computed<boolean>(() => get(isInitialLoading) && get(breakdown).length === 0);
</script>

<template>
  <div class="grid sm:grid-cols-3 gap-4">
    <RuiCard no-padding>
      <div class="flex flex-col gap-1 p-4">
        <h3 class="flex items-center min-h-8 -my-1 text-sm text-rui-text-secondary">
          {{ t('common.value') }}
        </h3>
        <FiatDisplay
          class="text-h5 font-semibold"
          :value="totalValue"
          :loading="showSkeleton"
        />
      </div>
    </RuiCard>
    <RuiCard no-padding>
      <div class="flex flex-col gap-1 p-4">
        <h3 class="flex items-center min-h-8 -my-1 text-sm text-rui-text-secondary">
          {{ t('common.assets') }}
        </h3>
        <div
          v-if="showSkeleton"
          class="flex items-center h-8"
        >
          <RuiSkeletonLoader class="w-12 h-6" />
        </div>
        <span
          v-else
          class="text-h5 font-semibold"
          data-testid="location-asset-count"
        >
          {{ breakdown.length }}
        </span>
      </div>
    </RuiCard>
  </div>
</template>
