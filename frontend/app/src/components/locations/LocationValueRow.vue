<script setup lang="ts">
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useLocationBalancesBreakdown } from '@/modules/balances/use-location-balances-breakdown';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { type BigNumber, Zero } from '@rotki/common';

const props = defineProps<{ identifier: string }>();

const { t } = useI18n({ useScope: 'global' });

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { balancesByLocation } = useLocationBalancesBreakdown();

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
