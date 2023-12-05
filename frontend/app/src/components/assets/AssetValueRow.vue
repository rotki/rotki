<script setup lang="ts">
import { type AssetPriceInfo } from '@/types/prices';

const props = withDefaults(
  defineProps<{
    identifier: string;
    isCollectionParent?: boolean;
  }>(),
  { isCollectionParent: false }
);

const { identifier, isCollectionParent } = toRefs(props);
const { assetPriceInfo } = useAggregatedBalances();

const info = computed<AssetPriceInfo>(() =>
  get(assetPriceInfo(identifier, isCollectionParent))
);

const { t } = useI18n();
</script>

<template>
  <div class="grid sm:grid-cols-3 gap-4">
    <RuiCard no-padding>
      <template #header>{{ t('common.price') }}</template>
      <AmountDisplay
        class="px-4 pb-4 text-h5 font-medium text-rui-text-secondary"
        :loading="!info.usdPrice || info.usdPrice.lt(0)"
        show-currency="symbol"
        :price-asset="identifier"
        :price-of-asset="info.usdPrice"
        fiat-currency="USD"
        :value="info.usdPrice"
      />
    </RuiCard>
    <RuiCard no-padding>
      <template #header>{{ t('assets.amount') }}</template>
      <AmountDisplay
        class="px-4 pb-4 text-h5 font-medium text-rui-text-secondary"
        :value="info.amount"
        :asset="identifier"
      />
    </RuiCard>
    <RuiCard no-padding>
      <template #header>{{ t('assets.value') }}</template>
      <AmountDisplay
        class="px-4 pb-4 text-h5 font-medium text-rui-text-secondary"
        show-currency="symbol"
        :amount="info.amount"
        :price-asset="identifier"
        :price-of-asset="info.usdPrice"
        fiat-currency="USD"
        :value="info.usdValue"
      />
    </RuiCard>
  </div>
</template>
