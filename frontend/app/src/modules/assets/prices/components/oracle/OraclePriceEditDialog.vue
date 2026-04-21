<script setup lang="ts">
import type { OraclePriceEntry } from '@/modules/assets/prices/price-types';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const modelValue = defineModel<OraclePriceEntry | undefined>({ required: true });

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getAssetField } = useAssetInfoRetrieval();
const { editHistoricalPrice } = useAssetPricesApi();
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
  <RuiDialog
    :model-value="!!modelValue"
    max-width="500"
    @update:model-value="!$event && (modelValue = undefined)"
  >
    <RuiCard>
      <template #header>
        {{ t('oracle_prices.edit.dialog.title') }}
      </template>
      <div class="flex flex-col gap-2">
        <div class="text-body-2 text-rui-text-secondary">
          {{ t('oracle_prices.edit.dialog.description', { fromAsset: fromSymbol, toAsset: toSymbol }) }}
        </div>
        <AmountInput
          v-model="editedPrice"
          variant="outlined"
          :label="t('common.price')"
        />
      </div>
      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          color="primary"
          @click="modelValue = undefined"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :loading="loading"
          :disabled="!editedPrice || loading"
          @click="save()"
        >
          {{ t('common.actions.save') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
