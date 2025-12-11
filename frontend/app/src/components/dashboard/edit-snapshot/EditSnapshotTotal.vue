<script setup lang="ts">
import type { BalanceSnapshot, LocationDataSnapshot } from '@/types/snapshots';
import { assert, type BigNumber, bigNumberify, One, Zero } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';
import { bigNumberSum } from '@/utils/calculation';
import { isNft } from '@/utils/nft';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<LocationDataSnapshot[]>({ required: true });

const props = defineProps<{
  timestamp: number;
  balancesSnapshot: BalanceSnapshot[];
}>();

const emit = defineEmits<{
  'update:step': [step: number];
}>();

const { t } = useI18n({ useScope: 'global' });

const { balancesSnapshot, timestamp } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { createKey, historicPriceInCurrentCurrency, isPending } = useHistoricCachePriceStore();

const total = ref<string>('');

const isCurrencyCurrencyUsd = computed<boolean>(() => get(currencySymbol) === CURRENCY_USD);

const rate = computed<BigNumber>(() => {
  if (get(isCurrencyCurrencyUsd))
    return One;
  return get(historicPriceInCurrentCurrency(CURRENCY_USD, get(timestamp)));
});

const fetchingRate = isPending(createKey(CURRENCY_USD, get(timestamp)));

const assetTotal = computed<BigNumber>(() => {
  const numbers = get(balancesSnapshot).map((item: BalanceSnapshot) => {
    if (item.category === 'asset')
      return item.usdValue;

    return item.usdValue.negated();
  });

  return bigNumberSum(numbers);
});

const locationTotal = computed<BigNumber>(() => {
  const numbers = get(modelValue).map((item: LocationDataSnapshot) => {
    if (item.location === 'total')
      return Zero;

    return item.usdValue;
  });

  return bigNumberSum(numbers);
});

const nftsTotal = computed<BigNumber>(() => {
  const numbers = get(balancesSnapshot).map((item: BalanceSnapshot) => {
    if (!isNft(item.assetIdentifier))
      return Zero;

    if (item.category === 'asset')
      return item.usdValue;

    return item.usdValue.negated();
  });

  return bigNumberSum(numbers);
});

const numericTotal = computed<BigNumber>(() => {
  const value = get(total);

  if (value === '')
    return Zero;

  return get(isCurrencyCurrencyUsd)
    ? bigNumberify(value)
    : bigNumberify(value).dividedBy(get(rate));
});

const nftsExcludedTotal = computed<BigNumber>(() => get(numericTotal).minus(get(nftsTotal)));

const suggestions = computed(() => {
  const assetTotalValue = get(assetTotal);
  const locationTotalValue = get(locationTotal);

  if (assetTotalValue.minus(locationTotalValue).abs().lt(1e-8) || !get(isCurrencyCurrencyUsd)) {
    return {
      total: assetTotalValue,
    };
  }
  return {
    asset: assetTotalValue,
    location: locationTotalValue,
  };
});

watchImmediate(rate, (rate) => {
  const totalEntry = get(modelValue).find((item: LocationDataSnapshot) => item.location === 'total');

  if (totalEntry) {
    const convertedFiatValue
        = get(isCurrencyCurrencyUsd)
          ? totalEntry.usdValue.toFixed()
          : totalEntry.usdValue.multipliedBy(get(rate)).toFixed();

    set(total, convertedFiatValue);
  }
});

function updateStep(step: number): void {
  emit('update:step', step);
}

function setTotal(number?: BigNumber) {
  assert(number);
  const convertedFiatValue = number.multipliedBy(get(rate)).toFixed();
  set(total, convertedFiatValue);
}

const rules = {
  total: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.total.rules.total'), required),
  },
};

const states = {
  total,
};

const v$ = useVuelidate(
  rules,
  states,
  { $autoDirty: true },
);

const suggestionsLabel = computed(() => ({
  asset: t('dashboard.snapshot.edit.dialog.total.use_calculated_asset', {
    length: get(balancesSnapshot).length,
  }),
  location: t('dashboard.snapshot.edit.dialog.total.use_calculated_location', {
    length: get(modelValue).length,
  }),
  total: t('dashboard.snapshot.edit.dialog.total.use_calculated_total'),
}));

async function save(): Promise<void> {
  if (!(await get(v$).$validate()))
    return;

  const val = get(modelValue);
  const index = val.findIndex((item: LocationDataSnapshot) => item.location === 'total')!;

  const newValue = [...val];

  newValue[index].usdValue = get(numericTotal);

  set(modelValue, newValue);
}
</script>

<template>
  <div>
    <div class="py-10 mx-auto max-w-[20rem]">
      <div class="text-h6 mb-4 text-center">
        {{ t('common.total') }}
      </div>
      <div class="mb-4">
        <AmountInput
          v-model="total"
          variant="outlined"
          :error-messages="toMessages(v$.total)"
          :disabled="fetchingRate"
        >
          <template
            v-if="fetchingRate"
            #append
          >
            <RuiProgress
              circular
              thickness="2"
              variant="indeterminate"
              color="primary"
              size="16"
            />
          </template>
        </AmountInput>

        <div class="text-rui-text-secondary text-caption">
          <i18n-t
            scope="global"
            keypath="dashboard.snapshot.edit.dialog.total.warning"
          >
            <template #amount>
              <AmountDisplay
                :value="nftsExcludedTotal"
                fiat-currency="USD"
              />
            </template>
          </i18n-t>
        </div>
      </div>
      <div>
        <div
          v-for="(number, key) in suggestions"
          :key="key"
        >
          <RuiButton
            color="primary"
            class="mb-4 w-full"
            @click="setTotal(number)"
          >
            <div class="flex flex-col items-center">
              <span>
                {{ suggestionsLabel[key] }}
              </span>
              <AmountDisplay
                v-if="number"
                class="text-2xl"
                :value="number"
                fiat-currency="USD"
                :timestamp="timestamp"
              />
            </div>
          </RuiButton>

          <div
            v-if="key === 'location'"
            class="text-rui-text-secondary text-caption"
          >
            {{ t('dashboard.snapshot.edit.dialog.total.hint') }}
          </div>
        </div>
      </div>
    </div>

    <div class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex justify-end p-2 gap-2">
      <RuiButton
        variant="text"
        @click="updateStep(2)"
      >
        <template #prepend>
          <RuiIcon name="lu-arrow-left" />
        </template>
        {{ t('common.actions.back') }}
      </RuiButton>
      <RuiButton
        color="primary"
        @click="save()"
      >
        {{ t('common.actions.finish') }}
        <template #append>
          <RuiIcon name="lu-arrow-right" />
        </template>
      </RuiButton>
    </div>
  </div>
</template>
