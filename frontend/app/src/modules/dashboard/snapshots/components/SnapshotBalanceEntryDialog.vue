<script setup lang="ts">
import type { BalanceSnapshot, BalanceSnapshotPayload, Snapshot } from '@/modules/dashboard/snapshots';
import type { BalanceMutation, LocationAttribution, LocationSplit } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { assert, type BigNumber, bigNumberify, Zero } from '@rotki/common';
import { BalanceType } from '@/modules/balances/types/balances';
import ConfirmSnapshotConflictReplacementDialog
  from '@/modules/dashboard/ConfirmSnapshotConflictReplacementDialog.vue';
import EditBalancesSnapshotForm from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotForm.vue';
import SnapshotLocationSplit from '@/modules/dashboard/snapshots/components/SnapshotLocationSplit.vue';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';
import { locationBalanceAfterEdit, type LocationBalancePreview, overdrawnLocationIds, soleEligibleLocation } from '@/modules/dashboard/snapshots/utils/snapshot-location-balance';
import { isLiability, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

type EditableBalance = BalanceSnapshot & { index: number };

const { snapshot, timestamp } = defineProps<{
  /** Current draft, read-only — used for the location preview and conflict check. */
  snapshot: Snapshot;
  timestamp: number;
}>();

const emit = defineEmits<{
  /** A validated add (index null) or edit (index set) of a balance row. */
  submit: [payload: { index: number | null; mutation: BalanceMutation }];
}>();

const { t } = useI18n({ useScope: 'global' });

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const open = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const submitting = ref<boolean>(false);
const editIndex = ref<number | null>(null);
const formModel = ref<(BalanceSnapshotPayload & { location: string }) | null>(null);
const conflictedBalanceSnapshot = ref<BalanceSnapshot | null>(null);
const splitMode = ref<boolean>(false);
const splits = ref<LocationSplit[]>([]);
const splitValid = ref<boolean>(false);

const form = useTemplateRef<InstanceType<typeof EditBalancesSnapshotForm>>('form');

// In a non-USD currency the fiat price/value the user edits can only be stored
// as USD via the historic forex rate; without it the stored value silently
// stops tracking, so block the save and point at the summary's FX control (#12277).
const { isUsd, loading, rateReady } = useHistoricFiatConversion(() => timestamp);
const rateMissing = computed<boolean>(() => !get(isUsd) && !get(rateReady));
// Only surface the dead-end once the lookup has settled, so it doesn't flash
// while the historic rate is still being fetched.
const showRateMissing = computed<boolean>(() => get(rateMissing) && !get(loading));

/** The balance's previous USD value (zero when adding). */
const previousUsdValue = computed<BigNumber>(() => {
  const idx = get(editIndex);
  return idx === null ? Zero : snapshot.balancesSnapshot[idx]?.usdValue ?? Zero;
});

/**
 * Signed change to the balance's USD value (`new − old`) — the amount the split
 * distributes across locations. On an add this is the whole new value; on an
 * edit it is only the difference, so each location moves by its own share rather
 * than the stale stored value being dumped on one row.
 */
const valueDelta = computed<BigNumber>(() =>
  bigNumberify(get(formModel)?.usdValue || '0').minus(get(previousUsdValue)));

/** The magnitude the split rows must add up to (the amount added or removed). */
const splitTotal = computed<BigNumber>(() => get(valueDelta).abs());

/** True when the edit lowers the value, so the split debits locations (and is capped). */
const splitIsRemoval = computed<boolean>(() => get(valueDelta).isNegative());

/**
 * Per-location USD subtotal, the most a removal-split row may take from it.
 * Only asset removals are capped (an increase credits, and liabilities may run
 * net-negative) — mirrors the delete dialog and `overdrawnLocationIds`.
 */
const splitCaps = computed<Record<string, BigNumber>>(() => {
  const formVal = get(formModel);
  if (!formVal || !get(splitIsRemoval) || isLiability(formVal.category))
    return {};
  return Object.fromEntries(
    snapshot.locationDataSnapshot
      .filter(item => item.location !== TOTAL_LOCATION)
      .map(item => [item.location, item.usdValue]),
  );
});

const existingLocations = computed<string[]>(() =>
  snapshot.locationDataSnapshot.filter(item => item.location !== TOTAL_LOCATION).map(item => item.location),
);

/**
 * Locations that can't absorb the edited value without going negative (asset
 * only) — disabled in the selector and rejected by the form's validation. On an
 * add this is always empty (attributing a fresh asset only raises a subtotal).
 */
const disabledLocations = computed<string[]>(() => {
  const formVal = get(formModel);
  if (!formVal)
    return [];
  const usdValue = bigNumberify(formVal.usdValue || '0');
  return overdrawnLocationIds(snapshot, formVal.category, location =>
    locationBalanceAfterEdit({ category: formVal.category, editIndex: get(editIndex), location, snapshot, usdValue }).after);
});

const previewLocationBalance = computed<LocationBalancePreview | null>(() => {
  const formVal = get(formModel);

  if (!formVal?.amount || !formVal.usdValue || !formVal.location)
    return null;

  // `formVal.usdValue` is already in USD (derived from the historic asset->USD
  // price); the user-currency conversion happens at the UI level, so no FX here.
  return locationBalanceAfterEdit({
    category: formVal.category,
    editIndex: get(editIndex),
    location: formVal.location,
    snapshot,
    usdValue: bigNumberify(formVal.usdValue),
  });
});

// Auto-select the only location that can absorb the entered value: when exactly
// one existing venue is eligible (not overdrawn) and the user hasn't picked one,
// preselect it — both the lone-location case and "only one holds enough". Watches
// value/category (not location), so a deliberate clear isn't immediately undone.
watch([
  (): string | undefined => get(formModel)?.usdValue,
  (): BalanceType | undefined => get(formModel)?.category,
], () => {
  const formVal = get(formModel);
  if (!formVal || get(splitMode) || formVal.location)
    return;
  const sole = soleEligibleLocation(get(existingLocations), get(disabledLocations));
  if (sole)
    set(formModel, { ...formVal, location: sole });
});

function resetSplit(): void {
  set(splitMode, false);
  set(splits, []);
  set(splitValid, false);
}

/**
 * Sensible default for the now-required location field: when the snapshot has a
 * single venue, preselect it (the overwhelmingly common case); otherwise leave
 * it empty so the user picks deliberately.
 */
function defaultLocation(): string {
  const locations = get(existingLocations);
  return locations.length === 1 ? locations[0] : '';
}

function openAdd(): void {
  set(editIndex, null);
  resetSplit();
  set(formModel, {
    amount: '',
    assetIdentifier: '',
    category: BalanceType.ASSET,
    location: defaultLocation(),
    timestamp,
    usdValue: '',
  });
  set(open, true);
}

function openEdit(item: EditableBalance): void {
  set(editIndex, item.index);
  resetSplit();

  // Snapshots store USD. The asset-price form re-derives the display value from
  // the historic asset->USD price, so pre-fill the raw USD value (no FX). This
  // is also the form's fallback when the historic price fetch fails, where a
  // main-currency-converted value would be persisted as USD and corrupt it.
  set(formModel, {
    ...item,
    amount: item.amount.toFixed(),
    location: defaultLocation(),
    usdValue: item.usdValue.toFixed(),
  });

  set(open, true);
}

function checkAssetExist(asset: string): void {
  // Only flag a conflict when adding (an edit already targets a row).
  if (get(editIndex) !== null)
    return;
  // Match on identifier AND category: the same asset held (ASSET) and owed
  // (LIABILITY) are distinct rows, so adding one when the other exists is fine.
  const category = get(formModel)?.category;
  const assetFound = snapshot.balancesSnapshot.find(
    item => item.assetIdentifier === asset && item.category === category,
  );
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
  const index = snapshot.balancesSnapshot.findIndex(item => item.assetIdentifier === assetIdentifier);

  if (index > -1)
    openEdit({ ...snapshot.balancesSnapshot[index], index });

  closeConflictDialog();
}

function close(): void {
  set(open, false);
  set(editIndex, null);
  set(formModel, null);
  resetSplit();
}

async function save(): Promise<void> {
  if (get(rateMissing))
    return;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return;

  const formData = get(formModel);
  if (!formData)
    return;

  // A split must add up to the balance's value before it can be applied.
  if (get(splitMode) && !get(splitValid))
    return;

  set(submitting, true);

  const balance: BalanceSnapshot = {
    amount: bigNumberify(formData.amount),
    assetIdentifier: formData.assetIdentifier,
    category: formData.category,
    timestamp,
    usdValue: bigNumberify(formData.usdValue),
  };

  set(submitting, false);

  // The split rows hold positive amounts; a removal moves the location subtotals
  // down, so negate each portion into the signed delta the mutation applies.
  const splitEntries: LocationSplit[] = get(splitIsRemoval)
    ? get(splits).map(entry => ({ ...entry, usdValue: entry.usdValue.negated() }))
    : get(splits);
  const location: LocationAttribution = get(splitMode) ? splitEntries : formData.location;
  emit('submit', { index: get(editIndex), mutation: { balance, location } });

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
    :action-disabled="rateMissing || (splitMode && !splitValid)"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="close()"
  >
    <RuiAlert
      v-if="showRateMissing"
      type="warning"
      class="mb-4"
    >
      {{ t('dashboard.snapshot.detail.fx_override.missing.description', { symbol: currencySymbol }) }}
    </RuiAlert>
    <EditBalancesSnapshotForm
      v-if="formModel"
      ref="form"
      v-model="formModel"
      v-model:state-updated="stateUpdated"
      :edit="editIndex !== null"
      :hide-location="splitMode"
      :preview-location-balance="previewLocationBalance"
      :disabled-locations="disabledLocations"
      :locations="editIndex !== null ? existingLocations : []"
      :timestamp="timestamp"
      @update:asset="checkAssetExist($event)"
    >
      <!-- Sits where the location selector's "only show existing" toggle used to
        be, so flipping split mode doesn't move it. -->
      <template #before-location>
        <RuiSwitch
          v-model="splitMode"
          color="primary"
          size="sm"
          hide-details
          data-testid="snapshot-balance-split-toggle"
        >
          {{ t('dashboard.snapshot.detail.split.title') }}
        </RuiSwitch>
      </template>
    </EditBalancesSnapshotForm>

    <SnapshotLocationSplit
      v-if="splitMode"
      v-model="splits"
      v-model:valid="splitValid"
      class="mt-3"
      :total="splitTotal"
      :locations="existingLocations"
      :max-per-location="splitCaps"
      :timestamp="timestamp"
    />

    <ConfirmSnapshotConflictReplacementDialog
      :snapshot="conflictedBalanceSnapshot"
      @cancel="cancelConvertToEdit()"
      @confirm="convertToEdit()"
    />
  </BigDialog>
</template>
