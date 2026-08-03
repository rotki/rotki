<script setup lang="ts">
import type { ActionStatus } from '@/modules/core/common/action';
import type { NewHistoryEventPayload } from '@/modules/history/events/schemas';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { assert, toSentenceCase } from '@rotki/common';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useEventPriceUpdate } from '@/modules/history/events/prices/use-event-price-update';
import ToggleLocationLink from '@/modules/history/management/forms/common/ToggleLocationLink.vue';
import { useEventPriceConversion } from '@/modules/history/management/forms/use-event-price-conversion';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import TwoFieldsAmountInput from '@/modules/shell/components/inputs/TwoFieldsAmountInput.vue';

interface HistoryEventAssetPriceFormProps {
  timestamp: number;
  disableAsset?: boolean;
  /**
   * Errors for the two fields this form owns, already resolved to strings. Deliberately not a
   * validator instance: the parent owns validation, this component only renders what it is given,
   * which is what lets Vuelidate and zod parents share it while the subtree migrates.
   */
  errorMessages: {
    amount: string[];
    /** Omitted by forms whose asset is fixed (`disableAsset`), which have no asset rule at all. */
    asset?: string[];
  };
  noPriceFields?: boolean;
  hidePriceFields?: boolean;
  location: string | undefined;
  disabled?: boolean;
  type?: string;
}

const amount = defineModel<string>('amount', { required: true });
const asset = defineModel<string | undefined>('asset', { required: true });
/**
 * The price write this form would perform, reported up so the parent can run it as part of saving
 * rather than reaching back in through a template ref. `undefined` means there is nothing to write.
 * Parents that still call {@link submitPrice} simply do not bind it.
 */
const priceIntent = defineModel<PriceIntent | undefined>('priceIntent', { required: false });

const {
  timestamp,
  disableAsset,
  errorMessages,
  noPriceFields,
  hidePriceFields,
  location,
  disabled,
  type,
} = defineProps<HistoryEventAssetPriceFormProps>();

const emit = defineEmits<{
  blur: [source: 'amount' | 'asset'];
}>();

const { t } = useI18n({ useScope: 'global' });

const chain = ref<string>();
const showPriceFields = ref<boolean>(!hidePriceFields && !noPriceFields);

const {
  modelAssetToFiatPrice,
  currencySymbol,
  fetchedAssetToFiatPrice,
  fetching,
  modelFiatValue,
  modelFiatValueFocused,
  reset,
} = useEventPriceConversion({
  amount,
  asset,
  showPriceFields,
  timestamp: () => timestamp,
});

const { updatePrice } = useEventPriceUpdate();

/**
 * Mirrors the condition {@link submitPrice} applies: only a price the user actually changed, for an
 * asset that is not the display currency, is worth writing.
 */
const pendingPriceIntent = computed<PriceIntent | undefined>(() => {
  if (noPriceFields || disabled)
    return undefined;

  const fromAsset = get(asset);
  const toAsset = get(currencySymbol);
  const price = get(modelAssetToFiatPrice);

  if (!fromAsset || fromAsset === toAsset || price === get(fetchedAssetToFiatPrice))
    return undefined;

  return { fromAsset, price, timestampMs: timestamp, toAsset };
});

async function submitPrice(payload?: NewHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> {
  if (noPriceFields || disabled)
    return { success: true };

  const assetVal = get(asset);
  assert(assetVal);

  try {
    const currency = get(currencySymbol);
    if (get(modelAssetToFiatPrice) !== get(fetchedAssetToFiatPrice) && assetVal !== currency) {
      await updatePrice({
        fromAsset: assetVal,
        mode: 'manual',
        price: get(modelAssetToFiatPrice),
        timestampMs: timestamp,
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

watchImmediate(pendingPriceIntent, (intent) => {
  set(priceIntent, intent);
});

defineExpose({
  reset,
  submitPrice,
});
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <AmountInput
        v-model="amount"
        variant="outlined"
        :data-cy="type ? `${type}-amount` : 'amount'"
        :disabled="disabled"
        :label="type ? t('transactions.events.form.asset_price.amount_label', { type: toSentenceCase((type)) }) : t('common.amount')"
        required
        :error-messages="errorMessages.amount"
        @blur="emit('blur', 'amount')"
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
          :error-messages="disableAsset ? [''] : errorMessages.asset ?? []"
          @blur="emit('blur', 'asset')"
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
      v-model:primary-value="modelAssetToFiatPrice"
      v-model:secondary-value="modelFiatValue"
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
      @update:reversed="modelFiatValueFocused = $event"
    />
  </div>
</template>
