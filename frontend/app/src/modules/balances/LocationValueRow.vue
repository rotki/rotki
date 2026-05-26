<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { bigNumberSum } from '@/modules/core/common/data/calculation';

const { identifier } = defineProps<{ identifier: string }>();

const { t } = useI18n({ useScope: 'global' });

const { useLocationBreakdown } = useAggregatedBalances();
const breakdown = useLocationBreakdown(() => identifier);

// Sum the breakdown directly so the tile always matches the table below.
// `balancesByLocation` doesn't expose chain-aliased keys (e.g. 'ethereum')
// and would otherwise undercount when a manual balance shares the alias label.
const totalValue = computed<BigNumber>(() => bigNumberSum(get(breakdown).map(entry => entry.value)));
</script>

<template>
  <div class="grid sm:grid-cols-3 gap-4">
    <RuiCard no-padding>
      <template #header>
        {{ t('locations.total_asset_price') }}
      </template>
      <FiatDisplay
        class="px-4 pb-4 text-h5 font-medium text-rui-text-secondary"
        :value="totalValue"
      />
    </RuiCard>
  </div>
</template>
