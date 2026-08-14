<script setup lang="ts">
import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import type { ProfitLossEvent } from '@/modules/reports/report-types';
import { z, type ZodType } from 'zod';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { requiredField } from '@/modules/core/form/fields';
import { useForm } from '@/modules/core/form/use-form';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

interface PriceState {
  price: string;
}

const { event, currency } = defineProps<{
  event: ProfitLossEvent;
  currency: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { resetHistoricalPricesData } = useHistoricPriceCache();
const { getHistoricPrice } = usePriceTaskManager();
const { addHistoricalPrice } = useAssetPricesApi();
const { setMessage } = useMessageStore();

const fetchingPrice = ref<boolean>(false);
const showDialog = ref<boolean>(false);

const schema = computed<ZodType>(() => z.object({
  price: requiredField(t('price_form.price_non_empty')),
}));

const form = useForm<PriceState, HistoricalPriceFormPayload>({
  initial: (): PriceState => ({ price: '' }),
  schema,
  submit: async (payload: HistoricalPriceFormPayload): Promise<{ message?: string; success: boolean }> => {
    try {
      await addHistoricalPrice(payload);
      resetHistoricalPricesData([payload]);
      return { success: true };
    }
    catch (error: unknown) {
      return { message: getErrorMessage(error), success: false };
    }
  },
  transform: (state): HistoricalPriceFormPayload => ({
    fromAsset: event.assetIdentifier,
    price: state.price,
    sourceType: PriceOracle.MANUAL,
    timestamp: event.timestamp,
    toAsset: currency,
  }),
});

async function openEditHistoricPriceDialog(): Promise<void> {
  set(showDialog, true);
  set(fetchingPrice, true);
  const { assetIdentifier, timestamp } = event;
  const historicPrice = await getHistoricPrice({
    fromAsset: assetIdentifier,
    timestamp,
    toAsset: currency,
  });
  form.state.price = historicPrice.isPositive() ? historicPrice.toFixed() : '0';
  set(fetchingPrice, false);
}

async function updatePrice(): Promise<void> {
  const result = await form.submit();
  if (result.outcome === 'success') {
    set(showDialog, false);
  }
  else if (result.outcome === 'error') {
    setMessage({
      description: t('price_management.add.error.description', { message: result.message ?? '' }),
      success: false,
      title: t('price_management.add.error.title'),
    });
  }
}
</script>

<template>
  <div class="flex justify-end">
    <RuiMenu :popper="{ placement: 'bottom-end' }">
      <template #activator="{ attrs }">
        <RuiButton
          variant="text"
          class="!p-2"
          icon
          v-bind="attrs"
        >
          <RuiIcon name="lu-ellipsis-vertical" />
        </RuiButton>
      </template>
      <RuiButton
        variant="list"
        data-testid="edit-historic-price-open"
        @click="openEditHistoricPriceDialog()"
      >
        <template #prepend>
          <RuiIcon name="lu-pencil-line" />
        </template>
        {{ t('profit_loss_events.edit_historic_price') }}
      </RuiButton>
    </RuiMenu>

    <RuiDialog
      v-model="showDialog"
      max-width="450px"
    >
      <form
        novalidate
        @submit.stop.prevent="updatePrice()"
      >
        <RuiCard>
          <template #header>
            {{ t('profit_loss_events.edit_historic_price') }}
          </template>

          <div class="flex flex-col gap-4">
            <AssetSelect
              :model-value="event.assetIdentifier"
              :label="t('price_form.from_asset')"
              hide-details
              disabled
              outlined
            />
            <AssetSelect
              :model-value="currency"
              :label="t('price_form.to_asset')"
              hide-details
              disabled
              outlined
            />
            <DateTimePicker
              :model-value="event.timestamp"
              disabled
              type="epoch"
              variant="outlined"
              hide-details
              :label="t('common.datetime')"
            />
            <AmountInput
              v-model="form.state.price"
              variant="outlined"
              :loading="fetchingPrice"
              :disabled="fetchingPrice"
              :label="t('common.price')"
              :error-messages="form.errors('price')"
              data-testid="edit-historic-price-value"
              @blur="form.touch('price')"
            />
          </div>

          <div class="text-body-2 text-rui-text-secondary">
            {{ t('profit_loss_events.edit_price_warning') }}
          </div>

          <template #footer>
            <div class="grow" />
            <RuiButton
              variant="text"
              color="primary"
              @click="showDialog = false"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>
            <RuiButton
              color="primary"
              type="submit"
            >
              {{ t('price_form.update_price') }}
            </RuiButton>
          </template>
        </RuiCard>
      </form>
    </RuiDialog>
  </div>
</template>
