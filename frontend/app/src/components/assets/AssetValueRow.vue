<script setup lang="ts">
import { type AssetPriceInfo } from '@/types/prices';

const props = defineProps({
  identifier: { required: true, type: String },
  isCollectionParent: { required: false, type: Boolean, default: false }
});

const { identifier, isCollectionParent } = toRefs(props);
const { assetPriceInfo } = useAggregatedBalances();

const info = computed<AssetPriceInfo>(() =>
  get(assetPriceInfo(identifier, isCollectionParent))
);

const { t } = useI18n();
</script>

<template>
  <VRow>
    <VCol>
      <VCard>
        <VCardTitle>
          <CardTitle>{{ t('common.price') }}</CardTitle>
        </VCardTitle>
        <VCardText class="text-end text-h5 font-weight-medium pt-4">
          <AmountDisplay
            v-if="info.usdPrice && info.usdPrice.gte(0)"
            show-currency="symbol"
            :price-asset="identifier"
            :price-of-asset="info.usdPrice"
            fiat-currency="USD"
            :value="info.usdPrice"
          />
          <div v-else class="pt-3 d-flex justify-end">
            <VSkeletonLoader height="20" width="70" type="text" />
          </div>
        </VCardText>
      </VCard>
    </VCol>
    <VCol>
      <VCard>
        <VCardTitle>
          <CardTitle>{{ t('assets.amount') }}</CardTitle>
        </VCardTitle>
        <VCardText class="text-end text-h5 font-weight-medium pt-4">
          <AmountDisplay :value="info.amount" :asset="identifier" />
        </VCardText>
      </VCard>
    </VCol>
    <VCol>
      <VCard>
        <VCardTitle>
          <CardTitle>{{ t('assets.value') }}</CardTitle>
        </VCardTitle>
        <VCardText class="text-end text-h5 font-weight-medium pt-4">
          <AmountDisplay
            show-currency="symbol"
            :amount="info.amount"
            :price-asset="identifier"
            :price-of-asset="info.usdPrice"
            fiat-currency="USD"
            :value="info.usdValue"
          />
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>
