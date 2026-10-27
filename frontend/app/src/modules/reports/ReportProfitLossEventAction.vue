<script setup lang="ts">
import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import type { ProfitLossEvent } from '@/modules/reports/report-types';
import { z, type ZodType } from 'zod';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { requiredField } from '@/modules/core/form/fields';
import { useForm } from '@/modules/core/form/use-form';
import TableFailureStrip from '@/modules/core/table/TableFailureStrip.vue';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

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

const fetchingPrice = ref<boolean>(false);
const showDialog = ref<boolean>(false);
/**
 * Why the last save failed, set even when the error carried no message; the dialog stays open with
 * the typed price, and Save is the retry.
 */
const saveError = shallowRef<string>();

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
  set(saveError, undefined);
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
  set(saveError, undefined);
  const result = await form.submit();
  if (result.outcome === 'success')
    set(showDialog, false);
  else if (result.outcome === 'error')
    set(saveError, result.message ?? '');
}
</script>

<template>
  <div class="flex justify-end">
    <RuiTooltip
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="text-rui-text-secondary"
          :aria-label="t('profit_loss_events.edit_historic_price')"
          data-testid="edit-historic-price-open"
          @click="openEditHistoricPriceDialog()"
        >
          <RuiIcon
            name="lu-pencil-line"
            size="16"
          />
        </RuiButton>
      </template>
      {{ t('profit_loss_events.edit_historic_price') }}
    </RuiTooltip>

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
            <TableFailureStrip
              v-if="saveError !== undefined"
              standalone
              :retryable="false"
              :title="t('price_management.add.error.title')"
              :message="saveError"
              data-testid="edit-historic-price-save-error"
            />
            <dl
              class="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2 text-sm rounded-rui-control bg-rui-grey-50 dark:bg-rui-grey-900 px-3 py-2.5"
              data-testid="edit-historic-price-summary"
            >
              <dt class="text-rui-text-secondary">
                {{ t('common.asset') }}
              </dt>
              <dd class="min-w-0">
                <AssetDetails
                  :asset="event.assetIdentifier"
                  :display="{ inline: true, size: '20px' }"
                  :actions="{ hideMenu: true }"
                />
              </dd>
              <dt class="text-rui-text-secondary">
                {{ t('price_form.to_asset') }}
              </dt>
              <dd class="min-w-0">
                <AssetDetails
                  :asset="currency"
                  :display="{ inline: true, size: '20px' }"
                  :actions="{ hideMenu: true }"
                />
              </dd>
              <dt class="text-rui-text-secondary">
                {{ t('common.datetime') }}
              </dt>
              <dd>
                <DateDisplay :timestamp="event.timestamp" />
              </dd>
            </dl>
            <AmountInput
              v-model="form.state.price"
              :disabled="fetchingPrice"
              :label="t('common.price')"
              :hint="t('profit_loss_events.edit_price_warning')"
              :error-messages="form.errors('price')"
              data-testid="edit-historic-price-value"
              @blur="form.touch('price')"
            >
              <template
                v-if="fetchingPrice"
                #append
              >
                <RuiProgress
                  circular
                  variant="indeterminate"
                  size="16"
                  thickness="2"
                  color="primary"
                />
              </template>
            </AmountInput>
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
