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

function checkAssetType() {
  const formVal = get(form);
  if (isNft(formVal.assetIdentifier))
    set(assetType, 'nft');
}

onBeforeMount(() => {
  checkAssetType();
});

watch(form, () => {
  checkAssetType();
});

watch(assetType, (assetType) => {
  if (assetType === 'nft')
    set(amount, '1');
});

const rules = {
  category: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.category').toString(),
      required,
    ),
  },
  assetIdentifier: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.asset').toString(),
      required,
    ),
  },
  amount: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.amount').toString(),
      required,
    ),
  },
  usdValue: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.value').toString(),
      required,
    ),
  },
};

const { setValidation } = useEditBalancesSnapshotForm();

const v$ = setValidation(rules, form, {
  $autoDirty: true,
});

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
      <div class="text--secondary text-caption">
        {{ t('common.asset') }}
      </div>
      <div>
        <RuiRadioGroup
          v-model="assetType"
          color="primary"
          inline
          :disabled="edit"
        >
          <template #default>
            <RuiRadio
              :label="t('dashboard.snapshot.edit.dialog.balances.token')"
              internal-value="token"
            />
            <RuiRadio
              :label="t('dashboard.snapshot.edit.dialog.balances.nft')"
              internal-value="nft"
            />
          </template>
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
          @blur="updateAsset($event.target.value)"
        />
      </div>
    </div>
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <AmountInput
        v-model="amount"
        :disabled="assetType === 'nft'"
        variant="outlined"
        :label="t('common.amount')"
        :error-messages="toMessages(v$.amount)"
      />
      <AmountInput
        v-model="usdValue"
        variant="outlined"
        :label="
          t('common.value_in_symbol', {
            symbol: currencySymbol,
          })
        "
        :error-messages="toMessages(v$.usdValue)"
      />
    </div>

    <EditBalancesSnapshotLocationSelector
      v-model="location"
      :locations="locations"
      :preview-location-balance="previewLocationBalance"
    />
  </form>
</template>
