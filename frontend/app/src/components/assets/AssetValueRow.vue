<script setup lang="ts">
import type { AssetPriceInfo, ManualPriceFormPayload } from '@/types/prices';

const props = withDefaults(
  defineProps<{
    identifier: string;
    isCollectionParent?: boolean;
  }>(),
  { isCollectionParent: false },
);

const { identifier, isCollectionParent } = toRefs(props);
const { assetPriceInfo } = useAggregatedBalances();

const { assetName } = useAssetInfoRetrieval();

const info = computed<AssetPriceInfo>(() => get(assetPriceInfo(identifier, isCollectionParent)));

const { isManualAssetPrice } = useBalancePricesStore();
const isManualPrice = isManualAssetPrice(identifier);

const { t } = useI18n();

const customPrice = ref<Partial<ManualPriceFormPayload> | null>(null);

const { setPostSubmitFunc, setOpenDialog } = useLatestPriceForm();
const { show } = useConfirmStore();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const { exchangeRate } = useBalancePricesStore();

function setPriceForm() {
  const toAsset = get(currencySymbol);
  setOpenDialog(true);
  set(customPrice, {
    fromAsset: get(identifier),
    toAsset,
    price: get(info)
      .price
      .multipliedBy(get(exchangeRate(toAsset)) ?? One)
      .toFixed(),
  });
}

const { refreshCurrentPrices, deletePrice, refreshing } = useLatestPrices(t);

function showDeleteConfirmation() {
  const identifierVal = get(identifier);
  show(
    {
      title: t('assets.custom_price.delete.tooltip'),
      message: t('assets.custom_price.delete.message', {
        asset: get(assetName(identifierVal)) ?? identifierVal,
      }),
    },
    () => deletePrice({ fromAsset: identifierVal }),
  );
}

onMounted(() => {
  setPostSubmitFunc(() => refreshCurrentPrices());
});
</script>

<template>
  <div class="grid sm:grid-cols-3 gap-4">
    <RuiCard
      no-padding
      class="[&>div:first-child]:pb-3"
    >
      <template #header>
        {{ t('common.price') }}
      </template>
      <div class="px-4 pb-3 flex flex-wrap items-center gap-1 md:gap-3">
        <AmountDisplay
          class="flex-1 text-h5 font-medium text-rui-text-secondary"
          :loading="refreshing || !info.price || info.price.lt(0)"
          show-currency="symbol"
          :price-asset="identifier"
          :price-of-asset="info.price"
          :fiat-currency="currencySymbol"
          :value="info.price"
          no-scramble
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
      <template #header>
        {{ t('assets.amount') }}
      </template>
      <AmountDisplay
        class="px-4 pb-4 text-h5 font-medium text-rui-text-secondary"
        :value="info.amount"
        :asset="identifier"
        no-truncate
      />
    </RuiCard>
    <RuiCard no-padding>
      <template #header>
        {{ t('assets.value') }}
      </template>
      <AmountDisplay
        class="px-4 pb-4 text-h5 font-medium text-rui-text-secondary"
        :loading="refreshing"
        show-currency="symbol"
        :amount="info.amount"
        :price-asset="identifier"
        :price-of-asset="info.price"
        :fiat-currency="currencySymbol"
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
