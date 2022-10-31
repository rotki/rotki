<template>
  <div>
    <div class="py-10 d-flex flex-column align-center">
      <div :class="$style.wrapper">
        <div class="text-h6 mb-4 text-center">
          {{ tc('common.total') }}
        </div>
        <div class="mb-4">
          <v-form v-model="valid">
            <amount-input v-model="total" outlined :rules="totalRules" />

            <div class="text--secondary text-caption">
              <i18n path="dashboard.snapshot.edit.dialog.total.warning">
                <template #amount>
                  <amount-display
                    :value="nftsExcludedTotal"
                    fiat-currency="USD"
                  />
                </template>
              </i18n>
            </div>
          </v-form>
        </div>
        <div>
          <div v-for="(number, key) in suggestions" :key="key">
            <v-btn
              block
              color="primary"
              class="mb-4"
              :class="$style.button"
              large
              @click="setTotal(number)"
            >
              <div class="d-flex flex-column align-center">
                <span>
                  {{ suggestionsLabel[key] }}
                </span>
                <amount-display
                  :class="$style['button__amount']"
                  :value="number"
                  fiat-currency="USD"
                />
              </div>
            </v-btn>

            <div v-if="key === 'location'" class="text--secondary text-caption">
              {{ tc('dashboard.snapshot.edit.dialog.total.hint') }}
            </div>
          </div>
        </div>
      </div>
    </div>
    <v-sheet elevation="10" class="d-flex justify-end pa-4">
      <v-spacer />
      <v-btn class="mr-4" @click="updateStep(2)">
        <v-icon>mdi-chevron-left</v-icon>
        {{ tc('common.actions.back') }}
      </v-btn>
      <v-btn color="primary" :disabled="!valid" @click="save">
        {{ tc('common.actions.finish') }}
        <v-icon>mdi-chevron-right</v-icon>
      </v-btn>
    </v-sheet>
  </div>
</template>
<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { PropType } from 'vue';
import { bigNumberSum } from '@/filters';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';
import { BalanceSnapshot, LocationDataSnapshot } from '@/types/snapshots';
import { assert } from '@/utils/assertions';
import { bigNumberify, One, Zero } from '@/utils/bignumbers';
import { isNft } from '@/utils/nft';

const props = defineProps({
  value: {
    required: true,
    type: Array as PropType<LocationDataSnapshot[]>
  },
  timestamp: {
    required: true,
    type: Number
  },
  balancesSnapshot: {
    required: true,
    type: Array as PropType<BalanceSnapshot[]>
  }
});

const emit = defineEmits<{
  (e: 'update:step', step: number): void;
  (e: 'input', value: LocationDataSnapshot[]): void;
}>();

const { value, balancesSnapshot } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const total = ref<string>('');
const valid = ref<boolean>(false);

const { tc } = useI18n();

const { exchangeRate } = useBalancePricesStore();
const fiatExchangeRate = computed<BigNumber>(() => {
  return get(exchangeRate(get(currencySymbol))) ?? One;
});

const assetTotal = computed<BigNumber>(() => {
  const numbers = get(balancesSnapshot).map((item: BalanceSnapshot) => {
    if (item.category === 'asset') return item.usdValue;
    return item.usdValue.negated();
  });

  return bigNumberSum(numbers);
});

const locationTotal = computed<BigNumber>(() => {
  const numbers = get(value).map((item: LocationDataSnapshot) => {
    if (item.location === 'total') return Zero;
    return item.usdValue;
  });

  return bigNumberSum(numbers);
});

const nftsTotal = computed<BigNumber>(() => {
  const numbers = get(balancesSnapshot).map((item: BalanceSnapshot) => {
    if (!isNft(item.assetIdentifier)) return Zero;
    if (item.category === 'asset') return item.usdValue;
    return item.usdValue.negated();
  });

  return bigNumberSum(numbers);
});

const numericTotal = computed<BigNumber>(() => {
  const value = get(total);

  if (value === '') return Zero;

  return get(currencySymbol) === CURRENCY_USD
    ? bigNumberify(value)
    : bigNumberify(value).dividedBy(get(fiatExchangeRate));
});

const nftsExcludedTotal = computed<BigNumber>(() => {
  return get(numericTotal).minus(get(nftsTotal));
});

const suggestions = computed(() => {
  const assetTotalValue = get(assetTotal);
  const locationTotalValue = get(locationTotal);

  if (assetTotalValue.minus(locationTotalValue).abs().lt(1e-8)) {
    return {
      total: assetTotalValue
    };
  }
  return {
    asset: assetTotalValue,
    location: locationTotalValue
  };
});

onBeforeMount(() => {
  const totalEntry = get(value).find(item => item.location === 'total');

  if (totalEntry) {
    const convertedFiatValue =
      get(currencySymbol) === CURRENCY_USD
        ? totalEntry.usdValue.toFixed()
        : totalEntry.usdValue.multipliedBy(get(fiatExchangeRate)).toFixed();

    set(total, convertedFiatValue);
  }
});

const input = (value: LocationDataSnapshot[]) => {
  emit('input', value);
};

const updateStep = (step: number) => {
  emit('update:step', step);
};

const setTotal = (number?: BigNumber) => {
  assert(number);
  const convertedFiatValue =
    get(currencySymbol) === CURRENCY_USD
      ? number.toFixed()
      : number.multipliedBy(get(fiatExchangeRate)).toFixed();

  set(total, convertedFiatValue);
};

const save = () => {
  const val = get(value);
  const index = val.findIndex(item => item.location === 'total')!;

  let newValue = [...val];

  newValue[index].usdValue = get(numericTotal);

  input(newValue);
};

const totalRules = computed(() => [
  (v: string) => !!v || tc('dashboard.snapshot.edit.dialog.total.rules.total')
]);

const suggestionsLabel = computed(() => ({
  total: tc('dashboard.snapshot.edit.dialog.total.use_calculated_total'),
  asset: tc('dashboard.snapshot.edit.dialog.total.use_calculated_asset', 0, {
    length: get(balancesSnapshot).length
  }),
  location: tc(
    'dashboard.snapshot.edit.dialog.total.use_calculated_location',
    0,
    {
      length: get(value).length
    }
  )
}));
</script>
<style module lang="scss">
.wrapper {
  width: 350px;
}

.button {
  padding: 0.75rem 0 !important;
  height: auto !important;

  &__amount {
    font-size: 1.25rem;
    margin-top: 0.25rem;
  }
}
</style>
