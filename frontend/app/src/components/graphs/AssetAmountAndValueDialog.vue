<script setup lang="ts">
import { type BigNumber } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    value?: boolean;
    timestamp?: number;
    amount?: number;
    totalValue?: number;
    asset?: string;
  }>(),
  {
    value: false,
    timestamp: 0,
    amount: 0,
    totalValue: 0,
    asset: ''
  }
);

const emit = defineEmits<{
  (e: 'input', visible: boolean): void;
}>();

const updateVisibility = (visible: boolean) => {
  emit('input', visible);
};

const { timestamp, amount, totalValue } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const formattedAmount = computed<BigNumber | null>(() => {
  if (get(amount)) {
    return get(bigNumberifyFromRef(amount));
  }

  return null;
});

const formattedTotalValue = computed<BigNumber | null>(() => {
  if (get(totalValue)) {
    return get(bigNumberifyFromRef(totalValue));
  }

  return null;
});

const { t } = useI18n();
</script>

<template>
  <VDialog :value="value" max-width="600" @input="updateVisibility($event)">
    <RuiCard>
      <template #header>
        {{ t('premium_components.statistics.asset_amount_and_value_detail') }}
      </template>
      <div>
        <div class="text-rui-text-secondary">{{ t('common.datetime') }}:</div>
        <DateDisplay :timestamp="timestamp * 1000" class="font-bold" />
      </div>
      <div class="pt-2">
        <div class="text-rui-text-secondary">{{ t('common.amount') }}:</div>
        <div class="flex gap-4">
          <div>
            <AmountDisplay
              v-if="formattedAmount"
              :value="formattedAmount"
              :asset="asset"
              class="font-bold"
            />
          </div>
          <AssetIcon :identifier="asset" size="24" />
        </div>
        <div class="pt-2">
          <div class="text-rui-text-secondary">{{ t('common.total') }}:</div>
          <AmountDisplay
            v-if="formattedTotalValue"
            :value="formattedTotalValue"
            :fiat-currency="currencySymbol"
            class="font-bold"
          />
        </div>
      </div>
    </RuiCard>
  </VDialog>
</template>
