<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { BalanceSnapshotPayload } from '@/modules/dashboard/snapshots';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { isNft } from '@/modules/assets/nft-utils';
import { useFormStateWatcher } from '@/modules/core/common/use-form';
import { useRefPropVModel } from '@/modules/core/common/validation/model';
import { toMessages } from '@/modules/core/common/validation/validation';
import EditBalancesSnapshotAssetPriceForm from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotAssetPriceForm.vue';
import EditBalancesSnapshotLocationSelector from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotLocationSelector.vue';
import BalanceTypeInput from '@/modules/shell/components/inputs/BalanceTypeInput.vue';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const model = defineModel<BalanceSnapshotPayloadAndLocation>({ required: true });

const { locations, previewLocationBalance = null, timestamp } = defineProps<{
  edit?: boolean;
  locations: string[];
  previewLocationBalance?: Record<string, BigNumber> | null;
  timestamp: number;
}>();

const emit = defineEmits<{
  'update:asset': [asset: string];
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
const assetPriceForm = useTemplateRef<InstanceType<typeof EditBalancesSnapshotAssetPriceForm>>('assetPriceForm');

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
  <div class="flex flex-col gap-2">
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
  </div>
</template>
