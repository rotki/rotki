<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { helpers, required } from '@vuelidate/validators';
import { type BalanceSnapshotPayload } from '@/types/snapshots';
import { toMessages } from '@/utils/validation';

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
    previewLocationBalance: null
  }
);

const emit = defineEmits<{
  (e: 'update:form', data: BalanceSnapshotPayloadAndLocation): void;
  (e: 'update:asset', asset: string): void;
}>();

const { t } = useI18n();
const { form } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const assetType = ref<string>('token');

const updateForm = (partial: Partial<BalanceSnapshotPayloadAndLocation>) => {
  emit('update:form', {
    ...get(form),
    ...partial
  });
};

const checkAssetType = () => {
  const formVal = get(form);
  if (isNft(formVal.assetIdentifier)) {
    set(assetType, 'nft');
  }
};

onBeforeMount(() => {
  checkAssetType();
});

watch(form, () => {
  checkAssetType();
});

watch(assetType, assetType => {
  if (assetType === 'nft') {
    updateForm({ amount: '1' });
  }
});

const rules = {
  category: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.category').toString(),
      required
    )
  },
  assetIdentifier: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.asset').toString(),
      required
    )
  },
  amount: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.amount').toString(),
      required
    )
  },
  usdValue: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.value').toString(),
      required
    )
  }
};

const { valid, setValidation } = useEditBalancesSnapshotForm();

const v$ = setValidation(rules, form, {
  $autoDirty: true
});

const updateAsset = (asset: string) => {
  emit('update:asset', asset);
};
</script>

<template>
  <VForm :value="valid" class="pt-4">
    <div>
      <BalanceTypeInput
        :value="form.category"
        outlined
        :label="t('common.category')"
        :error-messages="toMessages(v$.category)"
        @input="updateForm({ category: $event })"
      />
    </div>
    <div class="mb-4">
      <div class="text--secondary text-caption">
        {{ t('common.asset') }}
      </div>
      <div>
        <VRadioGroup v-model="assetType" row class="mt-2" :disabled="edit">
          <VRadio
            :label="t('dashboard.snapshot.edit.dialog.balances.token')"
            value="token"
          />
          <VRadio
            :label="t('dashboard.snapshot.edit.dialog.balances.nft')"
            value="nft"
          />
        </VRadioGroup>
      </div>
      <AssetSelect
        v-if="assetType === 'token'"
        :value="form.assetIdentifier"
        outlined
        :disabled="edit"
        :show-ignored="true"
        :label="t('common.asset')"
        :enable-association="false"
        :error-messages="toMessages(v$.assetIdentifier)"
        @input="updateForm({ assetIdentifier: $event })"
        @change="updateAsset($event)"
      />
      <VTextField
        v-if="assetType === 'nft'"
        :value="form.assetIdentifier"
        :label="t('common.asset')"
        outlined
        :disabled="edit"
        :error-messages="toMessages(v$.assetIdentifier)"
        :hint="t('dashboard.snapshot.edit.dialog.balances.nft_hint')"
        @input="updateForm({ assetIdentifier: $event })"
        @blur="updateAsset($event.target.value)"
      />
    </div>
    <div class="mb-4">
      <AmountInput
        :disabled="assetType === 'nft'"
        :value="form.amount"
        outlined
        :label="t('common.amount')"
        :error-messages="toMessages(v$.amount)"
        @input="updateForm({ amount: $event })"
      />
    </div>
    <div class="mb-4">
      <AmountInput
        :value="form.usdValue"
        outlined
        :label="
          t('common.value_in_symbol', {
            symbol: currencySymbol
          })
        "
        :error-messages="toMessages(v$.usdValue)"
        @input="updateForm({ usdValue: $event })"
      />
    </div>

    <div>
      <EditBalancesSnapshotLocationSelector
        :value="form.location"
        :locations="locations"
        :preview-location-balance="previewLocationBalance"
        @input="updateForm({ location: $event })"
      />
    </div>
  </VForm>
</template>
