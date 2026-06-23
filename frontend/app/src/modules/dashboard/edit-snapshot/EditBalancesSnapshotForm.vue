<script setup lang="ts">
import type { BalanceSnapshotPayload } from '@/modules/dashboard/snapshots';
import type { LocationBalancePreview } from '@/modules/dashboard/snapshots/utils/snapshot-location-balance';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { isNft } from '@/modules/assets/nft-utils';
import { useFormStateWatcher } from '@/modules/core/common/use-form';
import { useRefPropVModel } from '@/modules/core/common/validation/model';
import { toMessages } from '@/modules/core/common/validation/validation';
import EditBalancesSnapshotAssetPriceForm from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotAssetPriceForm.vue';
import EditBalancesSnapshotLocationSelector from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotLocationSelector.vue';
import BalanceTypeInput from '@/modules/shell/components/inputs/BalanceTypeInput.vue';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const model = defineModel<BalanceSnapshotPayloadAndLocation>({ required: true });

const { disabledLocations = [], hideLocation = false, locations, previewLocationBalance = null, timestamp } = defineProps<{
  edit?: boolean;
  locations: string[];
  previewLocationBalance?: LocationBalancePreview | null;
  timestamp: number;
  /** Hides the single-location selector when the caller drives attribution itself (e.g. a split). */
  hideLocation?: boolean;
  /** Location ids that can't absorb the edited value; unselectable and rejected by validation. */
  disabledLocations?: string[];
}>();

const emit = defineEmits<{
  'update:asset': [asset: string];
}>();

defineSlots<{
  /** Rendered directly above the location selector (persists in split mode). */
  'before-location': () => any;
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
  // Required whenever the single-location selector is shown: every balance must
  // be attributed so the location subtotals reconcile with the net worth. In
  // split mode the selector is hidden and the split drives attribution instead.
  location: {
    required: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.location'),
      requiredIf(() => !hideLocation),
    ),
    // Reject a location that can't absorb the edited value without going negative.
    sufficient: helpers.withMessage(
      t('dashboard.snapshot.edit.dialog.balances.rules.location_insufficient'),
      (value: string) => !value || !disabledLocations.includes(value),
    ),
  },
};

const states = {
  category,
  location,
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

    <!-- Anchored above the location selector (and kept while it's hidden in split
      mode) so the caller's split toggle doesn't jump when the selector unmounts. -->
    <slot name="before-location" />

    <EditBalancesSnapshotLocationSelector
      v-if="!hideLocation"
      v-model="location"
      optional-show-existing
      :error-messages="toMessages(v$.location)"
      :disabled-locations="disabledLocations"
      :locations="locations"
      :preview-location-balance="previewLocationBalance"
      :timestamp="timestamp"
    />
  </div>
</template>
