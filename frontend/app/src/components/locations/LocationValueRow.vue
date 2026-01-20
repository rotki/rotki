<script setup lang="ts">
import { type BigNumber, Zero } from '@rotki/common';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { FiatDisplay } from '@/modules/amount-display';

const props = defineProps<{ identifier: string }>();

const { t } = useI18n({ useScope: 'global' });

const { balancesByLocation } = useAggregatedBalances();

const totalValue = computed<BigNumber>(() => {
  const locations = get(balancesByLocation);
  return locations?.[props.identifier] ?? Zero;
});
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
