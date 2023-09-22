<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { helpers, required } from '@vuelidate/validators';
import { CURRENCY_USD } from '@/types/currencies';
import {
  type BalanceSnapshot,
  type LocationDataSnapshot
} from '@/types/snapshots';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  value: LocationDataSnapshot[];
  timestamp: number;
  balancesSnapshot: BalanceSnapshot[];
}>();

const emit = defineEmits<{
  (e: 'update:step', step: number): void;
  (e: 'input', value: LocationDataSnapshot[]): void;
}>();

const { value, balancesSnapshot } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const total = ref<string>('');
const { t } = useI18n();

const { exchangeRate } = useBalancePricesStore();
const fiatExchangeRate = computed<BigNumber>(
  () => get(exchangeRate(get(currencySymbol))) ?? One
);

const assetTotal = computed<BigNumber>(() => {
  const numbers = get(balancesSnapshot).map((item: BalanceSnapshot) => {
    if (item.category === 'asset') {
      return item.usdValue;
    }
    return item.usdValue.negated();
  });

  return bigNumberSum(numbers);
});

const locationTotal = computed<BigNumber>(() => {
  const numbers = get(value).map((item: LocationDataSnapshot) => {
    if (item.location === 'total') {
      return Zero;
    }
    return item.usdValue;
  });

  return bigNumberSum(numbers);
});

const nftsTotal = computed<BigNumber>(() => {
  const numbers = get(balancesSnapshot).map((item: BalanceSnapshot) => {
    if (!isNft(item.assetIdentifier)) {
      return Zero;
    }
    if (item.category === 'asset') {
      return item.usdValue;
    }
    return item.usdValue.negated();
  });

  return bigNumberSum(numbers);
});

const numericTotal = computed<BigNumber>(() => {
  const value = get(total);

  if (value === '') {
    return Zero;
  }

  return get(currencySymbol) === CURRENCY_USD
    ? bigNumberify(value)
    : bigNumberify(value).dividedBy(get(fiatExchangeRate));
});

const nftsExcludedTotal = computed<BigNumber>(() =>
  get(numericTotal).minus(get(nftsTotal))
);

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

const { valid, setValidation, setSubmitFunc, trySubmit } =
  useEditTotalSnapshotForm();

const save = async () => {
  const val = get(value);
  const index = val.findIndex(item => item.location === 'total')!;

  const newValue = [...val];

  newValue[index].usdValue = get(numericTotal);

  input(newValue);
};

setSubmitFunc(save);

const rules = {
  total: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.total.rules.total'),
      required
    )
  }
};

const v$ = setValidation(
  rules,
  {
    total
  },
  { $autoDirty: true }
);

const suggestionsLabel = computed(() => ({
  total: t('dashboard.snapshot.edit.dialog.total.use_calculated_total'),
  asset: t('dashboard.snapshot.edit.dialog.total.use_calculated_asset', {
    length: get(balancesSnapshot).length
  }),
  location: t('dashboard.snapshot.edit.dialog.total.use_calculated_location', {
    length: get(value).length
  })
}));

const css = useCssModule();
</script>

<template>
  <div>
    <div class="py-10 flex flex-col items-center">
      <div :class="css.wrapper">
        <div class="text-h6 mb-4 text-center">
          {{ t('common.total') }}
        </div>
        <div class="mb-4">
          <VForm :value="valid">
            <AmountInput
              v-model="total"
              outlined
              :error-messages="toMessages(v$.total)"
            />

            <div class="text--secondary text-caption">
              <i18n path="dashboard.snapshot.edit.dialog.total.warning">
                <template #amount>
                  <AmountDisplay
                    :value="nftsExcludedTotal"
                    fiat-currency="USD"
                  />
                </template>
              </i18n>
            </div>
          </VForm>
        </div>
        <div>
          <div v-for="(number, key) in suggestions" :key="key">
            <RuiButton
              color="primary"
              class="mb-4 w-full"
              :class="css.button"
              large
              @click="setTotal(number)"
            >
              <div class="flex flex-col items-center">
                <span>
                  {{ suggestionsLabel[key] }}
                </span>
                <AmountDisplay
                  :class="css['button__amount']"
                  :value="number"
                  fiat-currency="USD"
                />
              </div>
            </RuiButton>

            <div v-if="key === 'location'" class="text--secondary text-caption">
              {{ t('dashboard.snapshot.edit.dialog.total.hint') }}
            </div>
          </div>
        </div>
      </div>
    </div>
    <VSheet elevation="10" class="flex justify-end pa-4">
      <VSpacer />
      <RuiButton class="mr-4" @click="updateStep(2)">
        <VIcon>mdi-chevron-left</VIcon>
        {{ t('common.actions.back') }}
      </RuiButton>
      <RuiButton color="primary" @click="trySubmit()">
        {{ t('common.actions.finish') }}
        <VIcon>mdi-chevron-right</VIcon>
      </RuiButton>
    </VSheet>
  </div>
</template>

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
