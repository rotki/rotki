<script setup lang="ts">
import type { BalanceSnapshot, BalanceSnapshotPayload, Snapshot } from '@/modules/dashboard/snapshots';
import { assert, bigNumberify } from '@rotki/common';
import { BalanceType } from '@/modules/balances/types/balances';
import ConfirmSnapshotConflictReplacementDialog
  from '@/modules/dashboard/ConfirmSnapshotConflictReplacementDialog.vue';
import EditBalancesSnapshotForm from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotForm.vue';
import { locationBalanceAfterEdit, type LocationBalancePreview } from '@/modules/dashboard/snapshots/lib/snapshot-location-balance';
import { rebuildSnapshotAfterBalanceChange } from '@/modules/dashboard/snapshots/lib/snapshot-mutations';
import { TOTAL_LOCATION } from '@/modules/dashboard/snapshots/lib/snapshot-totals';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

type EditableBalance = BalanceSnapshot & { index: number };

const modelValue = defineModel<Snapshot>({ required: true });

const { timestamp } = defineProps<{
  timestamp: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const submitting = ref<boolean>(false);
const editIndex = ref<number | null>(null);
const formModel = ref<(BalanceSnapshotPayload & { location: string }) | null>(null);
const conflictedBalanceSnapshot = ref<BalanceSnapshot | null>(null);

const form = useTemplateRef<InstanceType<typeof EditBalancesSnapshotForm>>('form');

const existingLocations = computed<string[]>(() =>
  get(modelValue).locationDataSnapshot.filter(item => item.location !== TOTAL_LOCATION).map(item => item.location),
);

const previewLocationBalance = computed<LocationBalancePreview | null>(() => {
  const formVal = get(formModel);

  if (!formVal?.amount || !formVal.usdValue || !formVal.location)
    return null;

  // `formVal.usdValue` is already in USD (derived from the historic asset→USD
  // price); the user-currency conversion happens at the UI level, so no FX here.
  return locationBalanceAfterEdit({
    category: formVal.category,
    editIndex: get(editIndex),
    location: formVal.location,
    snapshot: get(modelValue),
    usdValue: bigNumberify(formVal.usdValue),
  });
});

function openAdd(): void {
  set(editIndex, null);
  set(formModel, {
    amount: '',
    assetIdentifier: '',
    category: BalanceType.ASSET,
    location: '',
    timestamp,
    usdValue: '',
  });
  set(open, true);
}

function openEdit(item: EditableBalance): void {
  set(editIndex, item.index);

  // Snapshots store USD. The asset-price form re-derives the display value from
  // the historic asset->USD price, so pre-fill the raw USD value (no FX). This
  // is also the form's fallback when the historic price fetch fails, where a
  // main-currency-converted value would be persisted as USD and corrupt it.
  set(formModel, {
    ...item,
    amount: item.amount.toFixed(),
    location: '',
    usdValue: item.usdValue.toFixed(),
  });

  set(open, true);
}

function checkAssetExist(asset: string): void {
  const assetFound = get(modelValue).balancesSnapshot.find(item => item.assetIdentifier === asset);
  set(conflictedBalanceSnapshot, assetFound ?? null);
}

function closeConflictDialog(): void {
  set(conflictedBalanceSnapshot, null);
}

function cancelConvertToEdit(): void {
  const currentFormModel = get(formModel);
  if (currentFormModel) {
    set(formModel, {
      ...currentFormModel,
      assetIdentifier: '',
    });
  }

  closeConflictDialog();
}

function convertToEdit(): void {
  assert(conflictedBalanceSnapshot);
  const assetIdentifier = get(conflictedBalanceSnapshot)?.assetIdentifier;
  const index = get(modelValue).balancesSnapshot.findIndex(item => item.assetIdentifier === assetIdentifier);

  if (index > -1)
    openEdit({ ...get(modelValue).balancesSnapshot[index], index });

  closeConflictDialog();
}

function close(): void {
  set(open, false);
  set(editIndex, null);
  set(formModel, null);
}

async function save(): Promise<void> {
  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return;

  const formData = get(formModel);
  if (!formData)
    return;

  set(submitting, true);
  const index = get(editIndex);

  const balancesSnapshot = [...get(modelValue).balancesSnapshot];
  const payload = {
    amount: bigNumberify(formData.amount),
    assetIdentifier: formData.assetIdentifier,
    category: formData.category,
    timestamp,
    usdValue: bigNumberify(formData.usdValue),
  };

  if (index !== null)
    balancesSnapshot[index] = payload;
  else balancesSnapshot.unshift(payload);

  set(submitting, false);

  set(modelValue, rebuildSnapshotAfterBalanceChange({
    balancesSnapshot,
    location: formData.location,
    locationBalance: get(previewLocationBalance),
    snapshot: get(modelValue),
    timestamp,
  }));

  formRef?.submitPrice();
  close();
}

defineExpose({
  openAdd,
  openEdit,
});
</script>

<template>
  <BigDialog
    :display="open"
    :title="
      editIndex !== null
        ? t('dashboard.snapshot.edit.dialog.balances.edit_title')
        : t('dashboard.snapshot.edit.dialog.balances.add_title')
    "
    :primary-action="t('common.actions.save')"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="close()"
  >
    <EditBalancesSnapshotForm
      v-if="formModel"
      ref="form"
      v-model="formModel"
      v-model:state-updated="stateUpdated"
      :edit="editIndex !== null"
      :preview-location-balance="previewLocationBalance"
      :locations="editIndex !== null ? existingLocations : []"
      :timestamp="timestamp"
      @update:asset="checkAssetExist($event)"
    />

    <ConfirmSnapshotConflictReplacementDialog
      :snapshot="conflictedBalanceSnapshot"
      @cancel="cancelConvertToEdit()"
      @confirm="convertToEdit()"
    />
  </BigDialog>
</template>
