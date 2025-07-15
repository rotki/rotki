<script setup lang="ts">
import type { AssetPriceInfo, ManualPriceFormPayload } from '@/types/prices';
import { One } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import RowActions from '@/components/helper/RowActions.vue';
import LatestPriceFormDialog from '@/components/price-manager/latest/LatestPriceFormDialog.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalances } from '@/composables/balances';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useLatestPrices } from '@/composables/price-manager/latest';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useConfirmStore } from '@/store/confirm';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';

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
const { refreshPrice } = useBalances();
const { isLoading } = useStatusStore();

const refreshingPrices = isLoading(Section.PRICES);

const info = computed<AssetPriceInfo>(() => get(assetPriceInfo(identifier, isCollectionParent)));

const { isManualAssetPrice, useExchangeRate } = usePriceUtils();
const isManualPrice = isManualAssetPrice(identifier);

const { t } = useI18n({ useScope: 'global' });

const openPriceDialog = ref<boolean>(false);
const customPrice = ref<ManualPriceFormPayload | null>(null);

const { show } = useConfirmStore();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

function setPriceForm() {
  const toAsset = get(currencySymbol);
  set(customPrice, {
    fromAsset: get(identifier),
    price: get(info)
      .usdPrice
      .multipliedBy(get(useExchangeRate(toAsset)) ?? One)
      .toFixed(),
    toAsset,
  });
  set(openPriceDialog, true);
}

const { deletePrice, refreshCurrentPrices, refreshing } = useLatestPrices(t);

function showDeleteConfirmation() {
  const identifierVal = get(identifier);
  show(
    {
      message: t('assets.custom_price.delete.message', {
        asset: get(assetName(identifierVal)) ?? identifierVal,
      }),
      title: t('assets.custom_price.delete.tooltip'),
    },
    () => deletePrice({ fromAsset: identifierVal }),
  );
}
</script>

<template>
  <div class="grid sm:grid-cols-3 gap-4">
    <RuiCard
      no-padding
      class="[&>div:first-child]:pb-3"
    >
      <template #custom-header>
        <div class="px-4 pt-3 flex justify-between items-start">
          <CardTitle>{{ t('common.price') }}</CardTitle>
          <RuiTooltip :open-delay="200">
            <template #activator>
              <RuiButton
                variant="text"
                icon
                class="!p-2"
                :loading="refreshingPrices"
                @click="refreshPrice(identifier)"
              >
                <RuiIcon
                  name="lu-refresh-ccw"
                  size="18"
                />
              </RuiButton>
            </template>
            {{ t('assets.refresh_price') }}
          </RuiTooltip>
        </div>
      </template>
      <div class="px-4 pb-3 flex flex-wrap items-center gap-1 md:gap-3">
        <AmountDisplay
          class="flex-1 text-h5 font-medium text-rui-text-secondary"
          :loading="refreshing || !info.usdPrice || info.usdPrice.lt(0)"
          show-currency="symbol"
          :price-asset="identifier"
          :price-of-asset="info.usdPrice"
          fiat-currency="USD"
          :value="info.usdPrice"
          is-asset-price
        />

        <RowActions
          :delete-tooltip="t('assets.custom_price.delete.tooltip')"
          :edit-tooltip="t('assets.custom_price.edit.tooltip')"
          :no-delete="!isManualPrice"
          @delete-click="showDeleteConfirmation()"
          @edit-click="setPriceForm()"
        />
      </div>

      <LatestPriceFormDialog
        v-model:open="openPriceDialog"
        :editable-item="customPrice"
        :edit-mode="isManualPrice"
        disable-from-asset
        @refresh="refreshCurrentPrices()"
      />
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
        :price-of-asset="info.usdPrice"
        fiat-currency="USD"
        :value="info.usdValue"
      />
    </RuiCard>
  </div>
</template>
