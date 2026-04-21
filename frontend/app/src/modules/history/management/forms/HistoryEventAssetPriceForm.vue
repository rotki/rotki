<script setup lang="ts">
import type { Validation } from '@vuelidate/core';
import type { ActionStatus } from '@/modules/core/common/action';
import type { NewHistoryEventPayload } from '@/modules/history/events/schemas';
import { assert, toSentenceCase } from '@rotki/common';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { toMessages } from '@/modules/core/common/validation/validation';
import ToggleLocationLink from '@/modules/history/management/forms/common/ToggleLocationLink.vue';
import { useEventPriceConversion } from '@/modules/history/management/forms/use-event-price-conversion';
import { useEventPriceSave } from '@/modules/history/management/forms/use-event-price-save';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import TwoFieldsAmountInput from '@/modules/shell/components/inputs/TwoFieldsAmountInput.vue';

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

const chain = ref<string>();
const showPriceFields = ref<boolean>(!hidePriceFields && !noPriceFields);

const {
  assetToFiatPrice,
  currencySymbol,
  fetchedAssetToFiatPrice,
  fetching,
  fiatValue,
  fiatValueFocused,
  reset,
} = useEventPriceConversion({
  amount,
  asset,
  showPriceFields,
  timestamp: () => timestamp,
});

const { savePrice } = useEventPriceSave();

async function submitPrice(payload?: NewHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> {
  if (noPriceFields || disabled)
    return { success: true };

  const assetVal = get(asset);
  assert(assetVal);

  try {
    const currency = get(currencySymbol);
    if (get(assetToFiatPrice) !== get(fetchedAssetToFiatPrice) && assetVal !== currency)
      await savePrice(assetVal, currency, get(assetToFiatPrice), timestamp);

    return { success: true };
  }
  catch (error: unknown) {
    let message: ValidationErrors | string = getErrorMessage(error);
    if (error instanceof ApiValidationError && payload)
      message = error.getValidationErrors(payload);

    return { message, success: false };
  }
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
