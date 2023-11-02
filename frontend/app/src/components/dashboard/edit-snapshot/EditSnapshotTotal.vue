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

const { setValidation, setSubmitFunc, trySubmit } = useEditTotalSnapshotForm();

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
          outlined
          :error-messages="toMessages(v$.total)"
        />

        <div class="text--secondary text-caption">
          <i18n path="dashboard.snapshot.edit.dialog.total.warning">
            <template #amount>
              <AmountDisplay :value="nftsExcludedTotal" fiat-currency="USD" />
            </template>
          </i18n>
        </div>
      </div>
      <div>
        <div v-for="(number, key) in suggestions" :key="key">
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
                class="text-2xl"
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

    <div
      class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex justify-end p-2 gap-2"
    >
      <RuiButton variant="text" @click="updateStep(2)">
        <template #prepend>
          <RuiIcon name="arrow-left-line" />
        </template>
        {{ t('common.actions.back') }}
      </RuiButton>
      <RuiButton color="primary" @click="trySubmit()">
        {{ t('common.actions.finish') }}
        <template #append>
          <RuiIcon name="arrow-right-line" />
        </template>
      </RuiButton>
    </div>
  </div>
</template>
