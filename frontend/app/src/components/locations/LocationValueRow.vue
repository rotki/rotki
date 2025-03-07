<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useBalancesBreakdown } from '@/composables/balances/breakdown';
import { useGeneralSettingsStore } from '@/store/settings/general';

const props = defineProps<{ identifier: string }>();

const { identifier } = toRefs(props);

const { t } = useI18n();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { balancesByLocation } = useBalancesBreakdown();

const totalValue = computed<BigNumber>(() => {
  const locations = get(balancesByLocation);
  return locations?.[identifier.value] ?? Zero;
});
</script>

<template>
  <div class="grid sm:grid-cols-3 gap-4">
    <RuiCard no-padding>
      <template #header>
        {{ t('locations.total_asset_price') }}
      </template>
      <AmountDisplay
        class="px-4 pb-4 text-h5 font-medium text-rui-text-secondary"
        tooltip
        show-currency="symbol"
        :fiat-currency="currencySymbol"
        :amount="totalValue"
        :value="totalValue"
      />
    </RuiCard>
  </div>
</template>
