<script setup lang="ts">
import type { OraclePriceEntry } from '@/modules/assets/prices/price-types';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const modelValue = defineModel<OraclePriceEntry | undefined>({ required: true });

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getAssetField } = useAssetInfoRetrieval();
const { editHistoricalPrice } = useAssetPricesApi();
const { resetHistoricalPricesData } = useHistoricPriceCache();
const { showErrorMessage } = useNotifications();

const loading = ref<boolean>(false);
const editedPrice = ref<string>('');

watch(modelValue, (item) => {
  if (item)
    set(editedPrice, item.price.toFixed());
});

const fromSymbol = computed<string>(() => {
  const item = get(modelValue);
  return item ? getAssetField(item.fromAsset, 'symbol') : '';
});

const toSymbol = computed<string>(() => {
  const item = get(modelValue);
  return item ? getAssetField(item.toAsset, 'symbol') : '';
});

async function save(): Promise<void> {
  const item = get(modelValue);
  if (!item)
    return;

  set(loading, true);
  try {
    await editHistoricalPrice({
      fromAsset: item.fromAsset,
      price: get(editedPrice),
      sourceType: item.sourceType,
      timestamp: item.timestamp,
      toAsset: item.toAsset,
    });
    resetHistoricalPricesData([{ fromAsset: item.fromAsset, timestamp: item.timestamp }]);
    set(modelValue, undefined);
    emit('refresh');
  }
  catch (error: unknown) {
    showErrorMessage(
      t('oracle_prices.edit.error.title'),
      t('oracle_prices.edit.error.description', { message: getErrorMessage(error) }),
    );
  }
  finally {
    set(loading, false);
  }
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="t('oracle_prices.edit.dialog.title')"
    :action="{ primary: t('common.actions.save'), disabled: !editedPrice }"
    :layout="{ autoHeight: true, divide: true, maxWidth: '560px' }"
    :loading="loading"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <template #subtitle>
      <span class="inline-flex flex-wrap items-center gap-x-2">
        {{ t('oracle_prices.edit.dialog.description', { fromAsset: fromSymbol, toAsset: toSymbol }) }}
        <span
          v-if="modelValue"
          aria-hidden="true"
          class="size-1 rounded-full bg-current"
        />
        <DateDisplay
          v-if="modelValue"
          :timestamp="modelValue.timestamp"
        />
      </span>
    </template>
    <AmountInput
      v-model="editedPrice"
      :label="t('common.price')"
      data-testid="oracle-price-edit-input"
    />
  </BigDialog>
</template>
