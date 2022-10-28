<template>
  <v-form :value="value" class="pt-4" @input="input">
    <div>
      <balance-type-input
        :value="form.category"
        outlined
        :label="t('common.category')"
        :rules="categoryRules"
        @input="updateForm({ category: $event })"
      />
    </div>
    <div class="mb-4">
      <div class="text--secondary text-caption">
        {{ t('common.asset') }}
      </div>
      <div>
        <v-radio-group v-model="assetType" row class="mt-2">
          <v-radio
            :label="t('dashboard.snapshot.edit.dialog.balances.token')"
            value="token"
          />
          <v-radio
            :label="t('dashboard.snapshot.edit.dialog.balances.nft')"
            value="nft"
          />
        </v-radio-group>
      </div>
      <asset-select
        v-if="assetType === 'token'"
        :value="form.assetIdentifier"
        outlined
        :excludes="excludedAssets"
        :show-ignored="true"
        :label="tc('common.asset')"
        :enable-association="false"
        :rules="assetRules"
        @input="updateForm({ assetIdentifier: $event })"
      />
      <v-text-field
        v-if="assetType === 'nft'"
        :value="form.assetIdentifier"
        :label="t('common.asset')"
        outlined
        :rules="assetRules"
        :hint="t('dashboard.snapshot.edit.dialog.balances.nft_hint')"
        @input="updateForm({ assetIdentifier: $event })"
      />
    </div>
    <div class="mb-4">
      <amount-input
        :disabled="assetType === 'nft'"
        :value="form.amount"
        outlined
        :label="t('common.amount')"
        :rules="amountRules"
        @input="updateForm({ amount: $event })"
      />
    </div>
    <div class="mb-4">
      <amount-input
        :value="form.usdValue"
        outlined
        :label="
          t('common.value_in_symbol', {
            symbol: currencySymbol
          })
        "
        :rules="valueRules"
        @input="updateForm({ usdValue: $event })"
      />
    </div>

    <div>
      <edit-balances-snapshot-location-selector
        :value="form.location"
        :locations="locations"
        :preview-location-balance="previewLocationBalance"
        @input="updateForm({ location: $event })"
      />
    </div>
  </v-form>
</template>
<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { PropType } from 'vue';
import EditBalancesSnapshotLocationSelector from '@/components/dashboard/EditBalancesSnapshotLocationSelector.vue';
import BalanceTypeInput from '@/components/inputs/BalanceTypeInput.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { BalanceSnapshotPayload } from '@/types/snapshots';
import { isNft } from '@/utils/nft';

const props = defineProps({
  value: {
    required: false,
    type: Boolean,
    default: false
  },
  form: {
    required: true,
    type: Object as PropType<BalanceSnapshotPayload & { location: string }>
  },
  locations: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  },
  excludedAssets: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  },
  previewLocationBalance: {
    required: false,
    type: Object as PropType<Record<string, BigNumber> | null>,
    default: () => null
  }
});

const emit = defineEmits(['update:form', 'input']);

const { t, tc } = useI18n();
const { form, excludedAssets } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const assetType = ref<string>('token');

const input = (valid: boolean) => {
  emit('input', valid);
};

const updateForm = (
  partial: Partial<BalanceSnapshotPayload & { location: string }>
) => {
  emit('update:form', {
    ...(get(form) as BalanceSnapshotPayload),
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

const categoryRules = [
  (v: string) =>
    !!v ||
    t('dashboard.snapshot.edit.dialog.balances.rules.category').toString()
];
const assetRules = [
  (v: string) =>
    !!v || t('dashboard.snapshot.edit.dialog.balances.rules.asset').toString(),
  (v: string) =>
    !get(excludedAssets).includes(v) ||
    t(
      'dashboard.snapshot.edit.dialog.balances.rules.asset_non_duplicate'
    ).toString()
];
const amountRules = [
  (v: string) =>
    !!v || t('dashboard.snapshot.edit.dialog.balances.rules.amount').toString()
];
const valueRules = [
  (v: string) =>
    !!v || t('dashboard.snapshot.edit.dialog.balances.rules.value').toString()
];
</script>
