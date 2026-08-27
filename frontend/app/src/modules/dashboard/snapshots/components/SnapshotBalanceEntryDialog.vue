<script setup lang="ts">
import type { BalanceSnapshot, BalanceSnapshotPayload, Snapshot } from '@/modules/dashboard/snapshots';
import type { BalanceMutation, LocationAttribution, LocationSplit } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { assert, type BigNumber, Zero } from '@rotki/common';
import { BalanceType } from '@/modules/balances/types/balances';
import { parseNumericInput } from '@/modules/core/common/data/bignumbers';
import ConfirmSnapshotConflictReplacementDialog
  from '@/modules/dashboard/ConfirmSnapshotConflictReplacementDialog.vue';
import EditBalancesSnapshotForm from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotForm.vue';
import SnapshotLocationSplit from '@/modules/dashboard/snapshots/components/SnapshotLocationSplit.vue';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';
import { locationBalanceAfterEdit, type LocationBalancePreview, overdrawnLocationIds, soleEligibleLocation } from '@/modules/dashboard/snapshots/utils/snapshot-location-balance';
import { isLiability, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import { useSetting } from '@/modules/settings/use-setting';
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

const currencySymbol = useSetting('currencySymbol');

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

const { rateMissing, showRateMissing } = useHistoricFiatConversion(() => timestamp);

/** The balance's previous USD value (zero when adding). */
const previousUsdValue = computed<BigNumber>(() => {
  const idx = get(editIndex);
  return idx === null ? Zero : snapshot.balancesSnapshot[idx]?.usdValue ?? Zero;
});

/** What the value field holds, or Zero while it holds nothing a number can be read out of. */
const enteredUsdValue = computed<BigNumber>(() => parseNumericInput(get(formModel)?.usdValue ?? '', Zero));

/**
 * Signed change to the balance's USD value (`new − old`) — the amount the split
 * distributes across locations. On an add this is the whole new value; on an
 * edit it is only the difference, so each location moves by its own share rather
 * than the stale stored value being dumped on one row.
 */
const valueDelta = computed<BigNumber>(() => get(enteredUsdValue).minus(get(previousUsdValue)));

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
  const usdValue = get(enteredUsdValue);
  return overdrawnLocationIds(snapshot, formVal.category, location =>
    locationBalanceAfterEdit({ category: formVal.category, editIndex: get(editIndex), location, snapshot, usdValue }).after);
});

const previewLocationBalance = computed<LocationBalancePreview | null>(() => {
  const formVal = get(formModel);

  if (!formVal?.amount || !formVal.usdValue || !formVal.location)
    return null;

  return locationBalanceAfterEdit({
    category: formVal.category,
    editIndex: get(editIndex),
    location: formVal.location,
    snapshot,
    usdValue: get(enteredUsdValue),
  });
});

/**
 * Preselects the one location that can absorb the entered value, when exactly one existing venue is
 * eligible and the user has picked none. Covers both the lone-location case and "only one holds
 * enough".
 */
function preselectSoleEligibleLocation(): void {
  const formVal = get(formModel);
  if (!formVal || get(splitMode) || formVal.location)
    return;

  const sole = soleEligibleLocation(get(existingLocations), get(disabledLocations));
  if (sole)
    set(formModel, { ...formVal, location: sole });
}

watch([
  (): string | undefined => get(formModel)?.usdValue,
  (): BalanceType | undefined => get(formModel)?.category,
], preselectSoleEligibleLocation);

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

  set(formModel, {
    ...item,
    amount: item.amount.toFixed(),
    location: defaultLocation(),
    usdValue: item.usdValue.toFixed(),
  });

  set(open, true);
}

/**
 * Flags an add that would duplicate a row the snapshot already holds.
 *
 * @remarks
 * Only when adding, since an edit already targets a row. The match is on identifier *and* category,
 * because the same asset held and owed are distinct rows, so adding one while the other exists is
 * fine.
 *
 * @param asset - the identifier the user picked
 */
function checkAssetExist(asset: string): void {
  if (get(editIndex) !== null)
    return;

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

/**
 * The row the form describes, or undefined while the amount or the value holds no number.
 *
 * The schema gates the category and the location; the amount and the value are free text, and the
 * price sub-form's rules over them only decorate the fields. Reading them here is what keeps a
 * cleared field from being saved as a nought nobody entered, or from reaching a parse that throws.
 */
function toBalance(formData: BalanceSnapshotPayload): BalanceSnapshot | undefined {
  const amount = parseNumericInput(formData.amount);
  const usdValue = parseNumericInput(formData.usdValue);
  if (!amount || !usdValue)
    return undefined;

  return {
    amount,
    assetIdentifier: formData.assetIdentifier,
    category: formData.category,
    timestamp,
    usdValue,
  };
}

/**
 * Where the balance is attributed: the split rows, or the single location the form holds.
 *
 * The split rows hold positive amounts; a removal moves the location subtotals down, so negate each
 * portion into the signed delta the mutation applies.
 */
function toLocation(location: string): LocationAttribution {
  if (!get(splitMode))
    return location;

  const splitEntries: LocationSplit[] = get(splitIsRemoval)
    ? get(splits).map(entry => ({ ...entry, usdValue: entry.usdValue.negated() }))
    : get(splits);
  return splitEntries;
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
  const balance = toBalance(formData);
  set(submitting, false);

  if (!balance)
    return;

  emit('submit', { index: get(editIndex), mutation: { balance, location: toLocation(formData.location) } });

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
    :action="{
      disabled: rateMissing || (splitMode && !splitValid),
      primary: t('common.actions.save'),
    }"
    :loading="submitting"
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
