<script setup lang="ts">
import { type BigNumber } from '@rotki/common';

const props = defineProps({
  identifier: { required: true, type: String }
});

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
  <VRow>
    <VCol cols="4">
      <VCard>
        <VCardTitle>
          <CardTitle>{{ t('locations.total_asset_price') }}</CardTitle>
        </VCardTitle>
        <VCardText class="text-end text-h5 font-medium">
          <AmountDisplay
            class="pt-4"
            tooltip
            show-currency="symbol"
            :fiat-currency="currencySymbol"
            :amount="totalValue"
            :value="totalValue"
          />
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>
