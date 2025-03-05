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
}>();

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
  const detail = get(assetDetail);
  if (detail && detail.amount) {
    set(model, detail.amount.toFixed());
  }
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
  <div class="py-6">
    <AmountInput
      v-if="isAmountSelected"
      v-model="amountModel"
      :disabled="!address"
      raw-input
      variant="outlined"
      class="font-bold text-6xl text-center w-full outline-none bg-transparent placeholder:text-rui-grey-400"
      placeholder="0"
    />
    <AmountInput
      v-else
      v-model="valueModel"
      :disabled="!address"
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
  </div>
</template>
