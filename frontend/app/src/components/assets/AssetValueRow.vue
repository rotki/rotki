<script setup lang="ts">
import type { ManualPriceFormPayload } from '@/modules/prices/price-types';
import RowActions from '@/components/helper/RowActions.vue';
import LatestPriceFormDialog from '@/components/price-manager/latest/LatestPriceFormDialog.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useLatestPrices } from '@/composables/price-manager/latest';
import { useSectionStatus } from '@/composables/status';
import { AssetAmountDisplay, AssetValueDisplay, FiatDisplay } from '@/modules/amount-display/components';
import { Section } from '@/modules/common/status';
import { useConfirmStore } from '@/modules/common/use-confirm-store';
import { usePriceRefresh } from '@/modules/prices/use-price-refresh';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const { identifier, isCollectionParent = false } = defineProps<{
  identifier: string;
  isCollectionParent?: boolean;
}>();

const openPriceDialog = ref<boolean>(false);
const customPrice = ref<ManualPriceFormPayload | null>(null);

const { t } = useI18n({ useScope: 'global' });
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { deletePrice, refreshCurrentPrices, refreshing } = useLatestPrices(t);
const { useAssetPriceInfo } = useAggregatedBalances();
const { useAssetPrice, useIsManualAssetPrice } = usePriceUtils();
const { getAssetField } = useAssetInfoRetrieval();
const { refreshPrice } = usePriceRefresh();
const { isLoading: refreshingPrices } = useSectionStatus(Section.PRICES);
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
        <FiatDisplay
          class="flex-1 text-h5 font-medium text-rui-text-secondary"
          :value="info.price"
          :loading="pricesLoading"
          :price-asset="identifier"
        />

        <RowActions
          :delete-tooltip="t('assets.custom_price.delete.tooltip')"
          :edit-tooltip="t('assets.custom_price.edit.tooltip')"
          :no-delete="!isManualPrice"
          :disabled="pricesLoading"
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
      <AssetAmountDisplay
        class="px-4 pb-4 text-h5 font-medium text-rui-text-secondary"
        :amount="info.amount"
        :asset="identifier"
        no-truncate
      />
    </RuiCard>
    <RuiCard no-padding>
      <template #header>
        {{ t('assets.value') }}
      </template>
      <AssetValueDisplay
        class="px-4 pb-4 text-h5 font-medium text-rui-text-secondary"
        :asset="identifier"
        :amount="info.amount"
        :price="info.price"
        :value="info.value"
        :loading="refreshing"
      />
    </RuiCard>
  </div>
</template>
