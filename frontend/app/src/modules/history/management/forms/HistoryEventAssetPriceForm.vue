<script setup lang="ts">
import type { Validation } from '@vuelidate/core';
import type { ActionStatus } from '@/modules/common/action';
import type { NewHistoryEventPayload } from '@/modules/history/events/schemas';
import type { HistoricalPriceFormPayload } from '@/modules/prices/price-types';
import { assert, type BigNumber, toSentenceCase } from '@rotki/common';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import TwoFieldsAmountInput from '@/components/inputs/TwoFieldsAmountInput.vue';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { ApiValidationError, type ValidationErrors } from '@/modules/api/types/errors';
import { bigNumberifyFromRef } from '@/modules/common/data/bignumbers';
import { millisecondsToSeconds } from '@/modules/common/data/date';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { toMessages } from '@/modules/common/validation/validation';
import ToggleLocationLink from '@/modules/history/management/forms/common/ToggleLocationLink.vue';
import { useHistoricPriceCache } from '@/modules/prices/use-historic-price-cache';
import { usePriceTaskManager } from '@/modules/prices/use-price-task-manager';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskStore } from '@/modules/tasks/use-task-store';

interface HistoryEventAssetPriceFormProps {
  timestamp: number;
  disableAsset?: boolean;
  v$: Validation;
  noPriceFields?: boolean;
  hidePriceFields?: boolean;
  location: string | undefined;
  disabled?: boolean;
  type?: string;
}

const amount = defineModel<string>('amount', { required: true });
const asset = defineModel<string | undefined>('asset', { required: true });

const {
  timestamp,
  disableAsset,
  v$,
  noPriceFields,
  hidePriceFields,
  location,
  disabled,
  type,
} = defineProps<HistoryEventAssetPriceFormProps>();

const { t } = useI18n({ useScope: 'global' });

const fiatValue = ref<string>('');
const assetToFiatPrice = ref<string>('');
const fiatValueFocused = ref<boolean>(false);
const fetchedAssetToFiatPrice = ref<string>('');
const chain = ref<string>();
const showPriceFields = ref<boolean>(!hidePriceFields && !noPriceFields);

const { useIsTaskRunning } = useTaskStore();
const { resetHistoricalPricesData } = useHistoricPriceCache();
const { getHistoricPrice } = usePriceTaskManager();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { addHistoricalPrice } = useAssetPricesApi();

const fetching = useIsTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

const numericAssetToFiatPrice = bigNumberifyFromRef(assetToFiatPrice);
const numericFiatValue = bigNumberifyFromRef(fiatValue);
const numericAmount = bigNumberifyFromRef(amount);

async function savePrice(payload: HistoricalPriceFormPayload) {
  await addHistoricalPrice(payload);
  resetHistoricalPricesData([payload]);
}

function onAssetToFiatPriceChanged(forceUpdate = false) {
  if (get(amount) && get(assetToFiatPrice) && (!get(fiatValueFocused) || forceUpdate))
    set(fiatValue, get(numericAmount).multipliedBy(get(numericAssetToFiatPrice)).toFixed());
}

function onFiatValueChange() {
  if (get(amount) && get(fiatValueFocused))
    set(assetToFiatPrice, get(numericFiatValue).div(get(numericAmount)).toFixed());
}

async function fetchHistoricPrices() {
  const time = timestamp;
  const assetVal = get(asset);
  if (!time || !assetVal)
    return;

  const price: BigNumber = await getHistoricPrice({
    fromAsset: assetVal,
    timestamp: millisecondsToSeconds(time),
    toAsset: get(currencySymbol),
  });

  if (price.gte(0))
    set(fetchedAssetToFiatPrice, price.toFixed());
}

watchImmediate(
  [() => timestamp, asset, showPriceFields],
  async ([timestamp, asset, showPriceFields], [oldTimestamp, oldAsset, oldShowPriceFields]) => {
    if (timestamp !== oldTimestamp || asset !== oldAsset || (oldShowPriceFields && !showPriceFields))
      await fetchHistoricPrices();
  },
);

watch(fetchedAssetToFiatPrice, (price) => {
  set(assetToFiatPrice, price);
  onAssetToFiatPriceChanged(true);
});

watch(assetToFiatPrice, () => {
  onAssetToFiatPriceChanged();
});

watch(fiatValue, () => {
  onFiatValueChange();
});

watch(amount, () => {
  onAssetToFiatPriceChanged();
  onFiatValueChange();
});

async function submitPrice(payload?: NewHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> {
  if (noPriceFields || disabled)
    return { success: true };

  const assetVal = get(asset);
  assert(assetVal);

  try {
    const currency = get(currencySymbol);
    if (get(assetToFiatPrice) !== get(fetchedAssetToFiatPrice) && assetVal !== currency) {
      await savePrice({
        fromAsset: assetVal,
        price: get(assetToFiatPrice),
        timestamp: millisecondsToSeconds(timestamp),
        toAsset: currency,
      });
    }

    return { success: true };
  }
  catch (error: unknown) {
    let message: ValidationErrors | string = getErrorMessage(error);
    if (error instanceof ApiValidationError && payload)
      message = error.getValidationErrors(payload);

    return { message, success: false };
  }
}

function reset() {
  set(fetchedAssetToFiatPrice, '');
  set(assetToFiatPrice, '');
  set(fiatValue, '');
}

defineExpose({
  reset,
  submitPrice,
});
</script>

<template>
  <div>
    <div
      v-if="v$"
      class="grid md:grid-cols-2 gap-4 mb-4"
    >
      <AmountInput
        v-model="amount"
        variant="outlined"
        :data-cy="type ? `${type}-amount` : 'amount'"
        :disabled="disabled"
        :label="type ? t('transactions.events.form.asset_price.amount_label', { type: toSentenceCase((type)) }) : t('common.amount')"
        required
        :error-messages="toMessages(v$.amount)"
        @blur="v$.amount.$touch()"
      />
      <div class="flex">
        <AssetSelect
          v-model="asset"
          outlined
          show-ignored
          :disabled="disabled || disableAsset"
          :data-cy="type ? `${type}-asset` : 'asset'"
          :label="type ? t('transactions.events.form.asset_price.asset_label', { type: toSentenceCase((type)) }) : t('common.asset')"
          required
          :chain="chain"
          :error-messages="disableAsset ? [''] : toMessages(v$.asset)"
          @blur="v$.asset.$touch()"
        />
        <ToggleLocationLink
          v-model="chain"
          class="ml-3"
          :disabled="disableAsset || disabled"
          :location="location"
        />
        <div
          v-if="hidePriceFields && !noPriceFields"
          class="pt-1"
        >
          <RuiTooltip :open-delay="400">
            <template #activator>
              <RuiButton
                icon
                variant="text"
                @click="showPriceFields = !showPriceFields"
              >
                <RuiIcon
                  class="transition-all"
                  :class="{ '-rotate-180': showPriceFields }"
                  name="lu-chevron-down"
                />
              </RuiButton>
            </template>
            {{ t('profit_loss_events.edit_historic_price') }}
          </RuiTooltip>
        </div>
      </div>
    </div>
    <TwoFieldsAmountInput
      v-if="showPriceFields && !noPriceFields"
      v-model:primary-value="assetToFiatPrice"
      v-model:secondary-value="fiatValue"
      class="mb-4"
      :loading="fetching"
      :disabled="fetching || disabled"
      :label="{
        primary: t('transactions.events.form.asset_price.label', {
          symbol: currencySymbol,
        }),
        secondary: t('common.value_in_symbol', {
          symbol: currencySymbol,
        }),
      }"
      @update:reversed="fiatValueFocused = $event"
    />
  </div>
</template>
