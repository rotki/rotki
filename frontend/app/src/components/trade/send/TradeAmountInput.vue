<script setup lang="ts">
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useTradeAsset } from '@/composables/trade/asset';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { bigNumberify } from '@rotki/common';
import { get, set } from '@vueuse/core';
import { computed } from 'vue';

const model = defineModel<string>({ required: true });

const props = defineProps<{
  asset: string;
  chain: string;
  address?: string;
  max: string;
  amountExceeded: boolean;
  loading?: boolean;
}>();

const { t } = useI18n();

const { address, asset, chain } = toRefs(props);

const fiatValue = ref<string>('0');
const fiatValueToBigNumber = bigNumberifyFromRef(fiatValue);

const amountToBigNumber = bigNumberifyFromRef(model);

const isAmountSelected = ref<boolean>(true);

const { getAssetDetail } = useTradeAsset(address);
const assetDetail = getAssetDetail(asset, chain);

// Computed properties for conversion
const amountModel = computed({
  get: () => get(model),
  set: (value: string) => {
    set(model, value);
    const price = get(assetDetail)?.price;
    if (price) {
      set(fiatValue, bigNumberify(value || '0')
        .multipliedBy(price)
        .toString());
    }
  },
});

const valueModel = computed({
  get: () => get(fiatValue),
  set: (newValue: string) => {
    set(fiatValue, newValue);
    const price = get(assetDetail)?.price;
    if (price) {
      set(model, bigNumberify(newValue || '0')
        .dividedBy(price)
        .toString());
    }
  },
});

function swapInput() {
  set(isAmountSelected, !get(isAmountSelected));
}

function setMax() {
  set(amountModel, props.max);
}

watch(
  () => get(assetDetail)?.price,
  (newPrice) => {
    if (newPrice && get(model)) {
      set(fiatValue, bigNumberify(get(model))
        .multipliedBy(newPrice)
        .toString());
    }
    else {
      set(fiatValue, '0');
    }
  },
);

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
      <AmountInput
        v-if="isAmountSelected"
        v-model="amountModel"
        :disabled="!address || loading"
        raw-input
        variant="outlined"
        class="font-bold text-6xl text-center w-full outline-none bg-transparent placeholder:text-rui-grey-300 dark:placeholder:text-rui-grey-800"
        placeholder="0"
      />
      <AmountInput
        v-else
        v-model="valueModel"
        :disabled="!address || loading"
        raw-input
        variant="outlined"
        class="font-bold text-6xl text-center w-full outline-none bg-transparent placeholder:text-rui-grey-400"
        placeholder="0"
      />

      <div class="text-rui-grey-400 flex justify-center gap-1 items-center text-sm font-medium pt-2">
        <AmountDisplay
          v-if="isAmountSelected"
          force-currency
          :value="fiatValueToBigNumber"
          show-currency="symbol"
        />
        <AmountDisplay
          v-else
          :value="amountToBigNumber"
          :asset="asset"
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
