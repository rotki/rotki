<script setup lang="ts">
import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import { AssetAmountDisplay, AssetValueDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import LatestPriceFormDialog from '@/modules/assets/prices/latest/LatestPriceFormDialog.vue';
import { useLatestPrices } from '@/modules/assets/prices/use-latest-price-manager';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSetting } from '@/modules/settings/use-setting';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { identifier, isCollectionParent = false } = defineProps<{
  identifier: string;
  isCollectionParent?: boolean;
}>();

const openPriceDialog = ref<boolean>(false);
const customPrice = ref<ManualPriceFormPayload | null>(null);

const { t } = useI18n({ useScope: 'global' });
const currencySymbol = useSetting('currencySymbol');
const { deletePrice, refreshCurrentPrices, refreshing } = useLatestPrices(t);
const { useAssetPriceInfo } = useAggregatedBalances();
const { useAssetPrice, useIsManualAssetPrice } = usePriceUtils();
const { getAssetField } = useAssetInfoRetrieval();
const { refreshing: refreshingPrices, refreshPrice } = usePriceRefresh();
const { show } = useConfirmStore();

const info = useAssetPriceInfo(() => identifier, () => isCollectionParent);
const price = useAssetPrice(() => identifier);
const isManualPrice = useIsManualAssetPrice(() => identifier);

const pricesLoading = computed<boolean>(() => {
  const infoVal = get(info);
  return get(refreshing) || get(refreshingPrices) || !infoVal.price || infoVal.price.lt(0);
});

function setPriceForm() {
  const toAsset = get(currencySymbol);
  set(customPrice, {
    fromAsset: identifier,
    price: get(price)?.toFixed() ?? '0',
    toAsset,
  });
  set(openPriceDialog, true);
}

function showDeleteConfirmation() {
  show({
    message: t('assets.custom_price.delete.message', {
      asset: getAssetField(identifier, 'name') || identifier,
    }),
    title: t('assets.custom_price.delete.tooltip'),
  }, () => deletePrice({ fromAsset: identifier }));
}
</script>

<template>
  <div class="grid sm:grid-cols-3 gap-4">
    <RuiCard no-padding>
      <div class="flex flex-col gap-1 p-4">
        <div class="flex items-center min-h-8 -my-1">
          <h3 class="mr-auto text-sm text-rui-text-secondary">
            {{ t('common.price') }}
          </h3>
          <RuiTooltip :open-delay="400">
            <template #activator>
              <RuiButton
                variant="text"
                icon
                size="sm"
                class="text-rui-text-secondary!"
                :aria-label="t('assets.refresh_price')"
                :loading="refreshingPrices"
                @click="refreshPrice(identifier)"
              >
                <RuiIcon
                  name="lu-refresh-ccw"
                  size="16"
                />
              </RuiButton>
            </template>
            {{ t('assets.refresh_price') }}
          </RuiTooltip>
          <RowActions
            :delete-tooltip="t('assets.custom_price.delete.tooltip')"
            :edit-tooltip="t('assets.custom_price.edit.tooltip')"
            :no-delete="!isManualPrice"
            :disabled="pricesLoading"
            @delete-click="showDeleteConfirmation()"
            @edit-click="setPriceForm()"
          />
        </div>
        <FiatDisplay
          class="text-h5 font-semibold"
          :value="info.price"
          :loading="pricesLoading"
          :price-asset="identifier"
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
      <div class="flex flex-col gap-1 p-4">
        <h3 class="flex items-center min-h-8 -my-1 text-sm text-rui-text-secondary">
          {{ t('assets.amount') }}
        </h3>
        <AssetAmountDisplay
          class="text-h5 font-semibold"
          :amount="info.amount"
          :asset="identifier"
          no-truncate
        />
      </div>
    </RuiCard>
    <RuiCard no-padding>
      <div class="flex flex-col gap-1 p-4">
        <h3 class="flex items-center min-h-8 -my-1 text-sm text-rui-text-secondary">
          {{ t('assets.value') }}
        </h3>
        <AssetValueDisplay
          class="text-h5 font-semibold"
          :asset="identifier"
          :amount="info.amount"
          :price="info.price"
          :value="info.value"
          :loading="refreshing"
        />
      </div>
    </RuiCard>
  </div>
</template>
