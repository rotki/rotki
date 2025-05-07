<script setup lang="ts">
import type { BalanceSnapshotPayload } from '@/types/snapshots';
import type { BigNumber } from '@rotki/common';
import EditBalancesSnapshotAssetPriceForm from '@/components/dashboard/edit-snapshot/EditBalancesSnapshotAssetPriceForm.vue';
import EditBalancesSnapshotLocationSelector from '@/components/dashboard/edit-snapshot/EditBalancesSnapshotLocationSelector.vue';
import BalanceTypeInput from '@/components/inputs/BalanceTypeInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useRefPropVModel } from '@/utils/model';
import { isNft } from '@/utils/nft';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const model = defineModel<BalanceSnapshotPayloadAndLocation>({ required: true });

withDefaults(
  defineProps<{
    edit?: boolean;
    locations?: string[];
    previewLocationBalance?: Record<string, BigNumber> | null;
    timestamp: number;
  }>(),
  {
    edit: false,
    locations: () => [],
    previewLocationBalance: null,
  },
);

const emit = defineEmits<{
  (e: 'update:asset', asset: string): void;
}>();

interface BalanceSnapshotPayloadAndLocation extends BalanceSnapshotPayload {
  location: string;
}

const category = useRefPropVModel(model, 'category');
const assetIdentifier = useRefPropVModel(model, 'assetIdentifier');
const amount = useRefPropVModel(model, 'amount');
const usdValue = useRefPropVModel(model, 'usdValue');
const location = useRefPropVModel(model, 'location');

const { t } = useI18n({ useScope: 'global' });

const assetType = ref<string>('token');
const assetPriceForm = ref<InstanceType<typeof EditBalancesSnapshotAssetPriceForm>>();

const rules = {
  category: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.category'), required),
  },
};

const states = {
  category,
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
  },
);
useFormStateWatcher(states, stateUpdated);

function updateAsset(asset: string) {
  emit('update:asset', asset);
}

function checkAssetType() {
  if (isNft(get(assetIdentifier)))
    set(assetType, 'nft');
}

function submitPrice() {
  const form = get(assetPriceForm);
  if (form)
    form.submitPrice();
}

watch(assetType, (assetType) => {
  if (assetType === 'nft')
    set(amount, '1');
});

watchImmediate(model, () => {
  checkAssetType();
});

defineExpose({
  submitPrice,
  validate: () => get(v$).$validate(),
});
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
      </div>
    </div>

    <EditBalancesSnapshotAssetPriceForm
      ref="assetPriceForm"
      v-model:asset="assetIdentifier"
      v-model:amount="amount"
      v-model:usd-value="usdValue"
      :timestamp="timestamp"
      :disable-asset="edit"
      :nft="assetType === 'nft'"
      @update:asset="updateAsset($event)"
    />

    <EditBalancesSnapshotLocationSelector
      v-model="location"
      optional-show-existing
      :locations="locations"
      :preview-location-balance="previewLocationBalance"
    />
  </form>
</template>
