<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import type { BigNumber } from '@rotki/common';
import type { BalanceSnapshotPayload } from '@/types/snapshots';

interface BalanceSnapshotPayloadAndLocation extends BalanceSnapshotPayload {
  location: string;
}

const props = withDefaults(
  defineProps<{
    edit?: boolean;
    form: BalanceSnapshotPayloadAndLocation;
    locations?: string[];
    previewLocationBalance?: Record<string, BigNumber> | null;
  }>(),
  {
    edit: false,
    locations: () => [],
    previewLocationBalance: null,
  },
);

const emit = defineEmits<{
  (e: 'update:form', data: BalanceSnapshotPayloadAndLocation): void;
  (e: 'update:asset', asset: string): void;
}>();

const { t } = useI18n();
const { form } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const assetType = ref<string>('token');

const category = usePropVModel(props, 'form', 'category', emit);
const assetIdentifier = usePropVModel(props, 'form', 'assetIdentifier', emit);
const amount = usePropVModel(props, 'form', 'amount', emit);
const usdValue = usePropVModel(props, 'form', 'usdValue', emit);
const location = usePropVModel(props, 'form', 'location', emit);
const price = ref<string>('1');

const usdValueInputFocused = ref<boolean>(false);

function checkAssetType() {
  const formVal = get(form);
  if (isNft(formVal.assetIdentifier))
    set(assetType, 'nft');
}

function updatePrice(forceUpdate = false) {
  const value = get(usdValue);
  const amountVal = get(amount);
  if (value && amountVal && (get(usdValueInputFocused) || forceUpdate)) {
    set(
      price,
      bigNumberify(get(usdValue))
        .div(bigNumberify(get(amount)))
        .toFixed(),
    );
  }
}

function calculateValue(forceUpdate = false) {
  const priceVal = get(price);
  const amountVal = get(amount);
  if (priceVal && amountVal && (!get(usdValueInputFocused) || forceUpdate)) {
    set(
      usdValue,
      bigNumberify(get(price))
        .multipliedBy(bigNumberify(get(amount)))
        .toFixed(),
    );
  }
}

watchImmediate(form, () => {
  checkAssetType();
});

onBeforeMount(() => {
  updatePrice(true);
});

watch(amount, () => {
  updatePrice();
  calculateValue();
});

watch(price, () => {
  calculateValue();
});

watch(usdValue, () => {
  updatePrice();
});

watch(assetType, (assetType) => {
  if (assetType === 'nft')
    set(amount, '1');
});

const rules = {
  category: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.category'), required),
  },
  assetIdentifier: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.asset'), required),
  },
  amount: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.amount'), required),
  },
  price: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.price'), required),
  },
  usdValue: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.value'), required),
  },
};

const { setValidation } = useEditBalancesSnapshotForm();

const v$ = setValidation(
  rules,
  computed(() => ({ ...get(form), price })),
  {
    $autoDirty: true,
  },
);

function updateAsset(asset: string) {
  emit('update:asset', asset);
}
</script>

<template>
  <form class="flex flex-col gap-2">
    <BalanceTypeInput
      v-model="category"
      :label="t('common.category')"
      :error-messages="toMessages(v$.category)"
    />
    <div>
      <div class="text-rui-text-secondary text-caption">
        {{ t('common.asset') }}
      </div>
      <div>
        <RuiRadioGroup
          v-model="assetType"
          color="primary"
          inline
          :disabled="edit"
        >
          <RuiRadio
            :label="t('dashboard.snapshot.edit.dialog.balances.token')"
            value="token"
          />
          <RuiRadio
            :label="t('dashboard.snapshot.edit.dialog.balances.nft')"
            value="nft"
          />
        </RuiRadioGroup>
        <AssetSelect
          v-if="assetType === 'token'"
          v-model="assetIdentifier"
          outlined
          :disabled="edit"
          :show-ignored="true"
          :label="t('common.asset')"
          :enable-association="false"
          :error-messages="toMessages(v$.assetIdentifier)"
          @change="updateAsset($event)"
        />
        <RuiTextField
          v-else-if="assetType === 'nft'"
          v-model="assetIdentifier"
          :label="t('common.asset')"
          variant="outlined"
          color="primary"
          :disabled="edit"
          class="mb-1.5"
          :error-messages="toMessages(v$.assetIdentifier)"
          :hint="t('dashboard.snapshot.edit.dialog.balances.nft_hint')"
        />
        <!-- @blur="updateAsset($event.target.value)" temporarily removed until we figure out what's wrong -->
      </div>
    </div>
    <AmountInput
      v-model="amount"
      :disabled="assetType === 'nft'"
      variant="outlined"
      :label="t('common.amount')"
      :error-messages="toMessages(v$.amount)"
    />

    <TwoFieldsAmountInput
      v-model:primary-value="price"
      v-model:secondary-value="usdValue"
      data-cy="trade-rate"
      :label="{
        primary: t('common.price'),
        secondary: t('common.value_in_symbol', {
          symbol: currencySymbol,
        }),
      }"
      :error-messages="{
        primary: toMessages(v$.price),
        secondary: toMessages(v$.usdValue),
      }"
      @update:reversed="usdValueInputFocused = $event"
    />

    <EditBalancesSnapshotLocationSelector
      v-model="location"
      optional-show-existing
      :locations="locations"
      :preview-location-balance="previewLocationBalance"
    />
  </form>
</template>
