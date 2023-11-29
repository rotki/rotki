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

const { setValidation } = useEditBalancesSnapshotForm();

const v$ = setValidation(rules, form, {
  $autoDirty: true
});

const updateAsset = (asset: string) => {
  emit('update:asset', asset);
};
</script>

<template>
  <form class="flex flex-col gap-2">
    <BalanceTypeInput
      :value="form.category"
      outlined
      :label="t('common.category')"
      :error-messages="toMessages(v$.category)"
      @input="updateForm({ category: $event })"
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
        <RuiTextField
          v-else-if="assetType === 'nft'"
          :value="form.assetIdentifier"
          :label="t('common.asset')"
          variant="outlined"
          color="primary"
          :disabled="edit"
          class="mb-1.5"
          :error-messages="toMessages(v$.assetIdentifier)"
          :hint="t('dashboard.snapshot.edit.dialog.balances.nft_hint')"
          @input="updateForm({ assetIdentifier: $event })"
          @blur="updateAsset($event.target.value)"
        />
      </div>
    </div>
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <AmountInput
        :disabled="assetType === 'nft'"
        :value="form.amount"
        outlined
        :label="t('common.amount')"
        :error-messages="toMessages(v$.amount)"
        @input="updateForm({ amount: $event })"
      />
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

    <EditBalancesSnapshotLocationSelector
      :value="form.location"
      :locations="locations"
      :preview-location-balance="previewLocationBalance"
      @input="updateForm({ location: $event })"
    />
  </form>
</template>
