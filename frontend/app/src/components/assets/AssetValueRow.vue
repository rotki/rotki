<script setup lang="ts">
import { type Ref } from 'vue';
import {
  type AssetPriceInfo,
  type ManualPriceFormPayload
} from '@/types/prices';

const props = withDefaults(
  defineProps<{
    identifier: string;
    isCollectionParent?: boolean;
  }>(),
  { isCollectionParent: false }
);

const { identifier, isCollectionParent } = toRefs(props);
const { assetPriceInfo } = useAggregatedBalances();

const { assetName } = useAssetInfoRetrieval();

const info = computed<AssetPriceInfo>(() =>
  get(assetPriceInfo(identifier, isCollectionParent))
);

const { isManualAssetPrice } = useBalancePricesStore();
const isManualPrice = isManualAssetPrice(identifier);

const { t } = useI18n();

const customPrice: Ref<Partial<ManualPriceFormPayload> | null> = ref(null);

const { setPostSubmitFunc, setOpenDialog } = useLatestPriceForm();
const { show } = useConfirmStore();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const setPriceForm = () => {
  setOpenDialog(true);
  set(customPrice, {
    fromAsset: get(identifier),
    toAsset: get(currencySymbol),
    price: get(info).usdPrice.toFixed()
  });
};

const { refreshCurrentPrices, deletePrice, refreshing } = useLatestPrices(t);

const showDeleteConfirmation = () => {
  const identifierVal = get(identifier);
  show(
    {
      title: t('assets.custom_price.delete.tooltip'),
      message: t('assets.custom_price.delete.message', {
        asset: get(assetName(identifierVal)) ?? identifierVal
      })
    },
    () => deletePrice({ fromAsset: identifierVal })
  );
};

onMounted(() => {
  setPostSubmitFunc(() => refreshCurrentPrices(true));
});
</script>

<template>
  <div class="grid sm:grid-cols-3 gap-4">
    <RuiCard no-padding class="[&>div:first-child]:pb-3">
      <template #header>{{ t('common.price') }}</template>
      <div class="px-4 pb-3 flex flex-wrap items-center gap-1 md:gap-3">
        <AmountDisplay
          class="flex-1 text-h5 font-medium text-rui-text-secondary"
          :loading="refreshing || !info.usdPrice || info.usdPrice.lt(0)"
          show-currency="symbol"
          :price-asset="identifier"
          :price-of-asset="info.usdPrice"
          fiat-currency="USD"
          :value="info.usdPrice"
        />

        <RowActions
          :delete-tooltip="t('assets.custom_price.delete.tooltip')"
          :edit-tooltip="t('assets.custom_price.edit.tooltip')"
          :no-delete="!isManualPrice"
          @delete-click="showDeleteConfirmation()"
          @edit-click="setPriceForm()"
        />
      </div>
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
        :loading="refreshing"
        show-currency="symbol"
        :amount="info.amount"
        :price-asset="identifier"
        :price-of-asset="info.usdPrice"
        fiat-currency="USD"
        :value="info.usdValue"
      />
    </RuiCard>

    <LatestPriceFormDialog
      :value="customPrice"
      :edit-mode="isManualPrice"
      disable-from-asset
    />
  </div>
</template>
