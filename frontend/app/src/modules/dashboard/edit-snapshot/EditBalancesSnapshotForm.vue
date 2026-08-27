<script setup lang="ts">
import type { ZodType } from 'zod';
import type { BalanceSnapshotPayload } from '@/modules/dashboard/snapshots';
import type { LocationBalancePreview } from '@/modules/dashboard/snapshots/utils/snapshot-location-balance';
import { isNft } from '@/modules/assets/nft-utils';
import { useModelForm } from '@/modules/core/form/use-model-form';
import EditBalancesSnapshotAssetPriceForm from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotAssetPriceForm.vue';
import EditBalancesSnapshotLocationSelector from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotLocationSelector.vue';
import {
  type BalanceSnapshotFormState,
  balanceSnapshotSchema,
} from '@/modules/dashboard/edit-snapshot/snapshot-forms';
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

const { t } = useI18n({ useScope: 'global' });

const assetType = ref<string>('token');
const assetPriceForm = useTemplateRef<InstanceType<typeof EditBalancesSnapshotAssetPriceForm>>('assetPriceForm');

const schema = computed<ZodType>(() => balanceSnapshotSchema({
  disabledLocations,
  hideLocation,
  messages: {
    category: t('dashboard.snapshot.edit.dialog.balances.rules.category'),
    location: t('dashboard.snapshot.edit.dialog.balances.rules.location'),
    locationInsufficient: t('dashboard.snapshot.edit.dialog.balances.rules.location_insufficient'),
  },
}));

const form = useModelForm<BalanceSnapshotFormState>({
  model,
  schema,
  stateUpdated,
  transientKeys: ['amount', 'assetIdentifier', 'timestamp', 'usdValue'],
});

function updateAsset(asset: string) {
  emit('update:asset', asset);
}

function checkAssetType() {
  if (isNft(form.state.assetIdentifier))
    set(assetType, 'nft');
}

function submitPrice() {
  const form = get(assetPriceForm);
  if (form)
    form.submitPrice();
}

watch(assetType, (assetType) => {
  if (assetType === 'nft')
    form.state.amount = '1';
});

watchImmediate(model, checkAssetType, { deep: true });

defineExpose({
  submitPrice,
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <BalanceTypeInput
      v-model="form.state.category"
      data-testid="category"
      :label="t('common.category')"
      :error-messages="form.errors('category')"
      @update:model-value="form.touch('category')"
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
      v-model:asset="form.state.assetIdentifier"
      v-model:amount="form.state.amount"
      v-model:usd-value="form.state.usdValue"
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
      v-model="form.state.location"
      optional-show-existing
      :error-messages="form.errors('location')"
      :disabled-locations="disabledLocations"
      :locations="locations"
      :preview-location-balance="previewLocationBalance"
      :timestamp="timestamp"
      @update:model-value="form.touch('location')"
    />
  </div>
</template>
