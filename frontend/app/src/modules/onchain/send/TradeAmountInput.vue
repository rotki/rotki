<script setup lang="ts">
import { bigNumberify } from '@rotki/common';
import { get, set } from '@vueuse/core';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/amount-display/components';
import { useTradableAsset } from '@/modules/onchain/use-tradable-asset';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { bigNumberifyFromRef } from '@/utils/bignumbers';

const model = defineModel<string>({ required: true });

const props = defineProps<{
  asset: string;
  chain: string;
  address?: string;
  max: string;
  amountExceeded: boolean;
  loading?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { address, asset, chain } = toRefs(props);

const fiatValue = ref<string>('0');
const isAmountSelected = ref<boolean>(true);

const { currency } = storeToRefs(useGeneralSettingsStore());

const { getAssetDetail } = useTradableAsset(address);
const assetDetail = getAssetDetail(asset, chain);
const price = useRefMap(assetDetail, m => m?.price);
const fiatValueToBigNumber = bigNumberifyFromRef(fiatValue);
const amountToBigNumber = bigNumberifyFromRef(model);

const fiatValuePlaceholder = computed<string>(() => `${get(currency).unicodeSymbol}0`);
const displayValue = computed<string>(() => get(isAmountSelected) ? get(model) : get(fiatValue));

/**
 * Dynamically scales the input font size to prevent text overflow.
 *
 * Starts at 3.75rem (text-6xl) for up to MAX_DIGITS characters and scales down
 * proportionally (BASE * MAX_DIGITS / length) for longer values, accounting for
 * thousand and decimal separators in the visual length. Rounded to the nearest
 * 0.05rem for smoother transitions, clamped to a 1.5rem minimum.
 */
const BASE_FONT_SIZE = 3.75;
const MAX_DIGITS = 12;
const MIN_FONT_SIZE = 1.5;
const ROUND_STEP = 0.05;

function getVisualLength(value: string): number {
  const parts = value.split('.');
  const integerPart = parts[0] || '';
  const digitCount = integerPart.replace(/^-/, '').length;
  const thousandSeparators = Math.max(0, Math.floor((digitCount - 1) / 3));
  return value.length + thousandSeparators;
}

const dynamicFontSize = computed<string>(() => {
  const length = getVisualLength(get(displayValue));
  if (length <= MAX_DIGITS)
    return `${BASE_FONT_SIZE}rem`;

  const size = Math.max(Math.round((BASE_FONT_SIZE * MAX_DIGITS / length) / ROUND_STEP) * ROUND_STEP, MIN_FONT_SIZE);
  return `${size}rem`;
});

function swapInput(): void {
  set(isAmountSelected, !get(isAmountSelected));
}

function setMax(): void {
  set(model, props.max);
  const priceVal = get(price);
  if (get(isAmountSelected) && priceVal) {
    set(fiatValue, bigNumberify(props.max).multipliedBy(priceVal).toString());
  }
}

watch([model, price], ([value, price]) => {
  if (!get(isAmountSelected))
    return;

  if (value && price) {
    set(fiatValue, bigNumberify(value).multipliedBy(price).toString());
  }
  else {
    set(fiatValue, '0');
  }
});

watch([fiatValue, price], ([fiatValue, price]) => {
  if (get(isAmountSelected))
    return;

  if (fiatValue && price) {
    set(model, bigNumberify(fiatValue).dividedBy(price).toString());
  }
  else {
    set(model, '0');
  }
});

defineExpose({
  setMax,
});
</script>

<template>
  <div class="border border-default rounded-t-lg bg-rui-grey-50 dark:bg-rui-grey-900 p-3 relative overflow-hidden">
    <RuiProgress
      v-if="loading"
      class="absolute top-0 left-0"
      thickness="2"
      color="primary"
      variant="indeterminate"
    />
    <div class="text-rui-grey-500 text-sm font-medium">
      {{ t('trade.amount.sending') }}
    </div>
    <div class="pt-6 pb-2">
      <div
        class="flex items-end"
        :style="{ height: `${BASE_FONT_SIZE}rem` }"
      >
        <AmountInput
          v-if="isAmountSelected"
          v-model="model"
          :disabled="!address || loading"
          raw-input
          variant="outlined"
          :style="{ fontSize: dynamicFontSize }"
          class="font-bold text-center w-full outline-none bg-transparent placeholder:text-rui-grey-300 dark:placeholder:text-rui-grey-800"
          placeholder="0"
        />
        <AmountInput
          v-else
          v-model="fiatValue"
          :disabled="!address || loading"
          raw-input
          variant="outlined"
          :style="{ fontSize: dynamicFontSize }"
          class="font-bold text-center w-full outline-none bg-transparent placeholder:text-rui-grey-300 dark:placeholder:text-rui-grey-800"
          :placeholder="fiatValuePlaceholder"
        />
      </div>

      <div class="text-rui-grey-400 flex justify-center gap-1 items-center text-sm font-medium pt-2">
        <FiatDisplay
          v-if="isAmountSelected"
          :value="fiatValueToBigNumber"
          no-scramble
        />
        <AssetAmountDisplay
          v-else
          :asset="asset"
          :amount="amountToBigNumber"
          no-scramble
        />
        <RuiButton
          icon
          size="sm"
          variant="text"
          @click="swapInput()"
        >
          <RuiIcon
            class="text-rui-grey-400"
            name="lu-arrow-down-up"
            size="12"
          />
        </RuiButton>
      </div>

      <div class="text-sm text-center text-rui-error pt-2 h-6">
        <span v-if="amountExceeded">{{ t('trade.amount.insufficient') }}</span>
      </div>
    </div>
  </div>
</template>
