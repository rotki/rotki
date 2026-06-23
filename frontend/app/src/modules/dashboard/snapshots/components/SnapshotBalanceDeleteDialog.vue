<script setup lang="ts">
import type { Snapshot } from '@/modules/dashboard/snapshots';
import type { LocationAttribution, LocationSplit } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { type BigNumber, Zero } from '@rotki/common';
import EditBalancesSnapshotLocationSelector from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotLocationSelector.vue';
import SnapshotLocationSplit from '@/modules/dashboard/snapshots/components/SnapshotLocationSplit.vue';
import { locationBalanceAfterDelete, type LocationBalancePreview, overdrawnLocationIds, soleEligibleLocation } from '@/modules/dashboard/snapshots/utils/snapshot-location-balance';
import { isLiability, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';

const { snapshot, timestamp } = defineProps<{
  snapshot: Snapshot;
  timestamp: number;
}>();

const emit = defineEmits<{
  confirm: [payload: { index: number; location: LocationAttribution }];
}>();

const { t } = useI18n({ useScope: 'global' });

const index = ref<number | null>(null);
const location = ref<string>('');
const splitMode = ref<boolean>(false);
const splits = ref<LocationSplit[]>([]);
const splitValid = ref<boolean>(false);

const display = computed<boolean>(() => get(index) !== null);

const existingLocations = computed<string[]>(() =>
  snapshot.locationDataSnapshot.filter(item => item.location !== TOTAL_LOCATION).map(item => item.location),
);

/** The balance being removed (null while the dialog is closed). */
const removed = computed(() => {
  const current = get(index);
  return current === null ? null : snapshot.balancesSnapshot[current] ?? null;
});

/** USD value of the row being deleted; the split must add up to it. */
const total = computed<BigNumber>(() => get(removed)?.usdValue ?? Zero);

/**
 * Locations that can't absorb this removal without going negative (asset only).
 * Rendered unselectable in single mode and capped per row when splitting.
 */
const disabledLocations = computed<string[]>(() => {
  const current = get(index);
  const balance = get(removed);
  if (current === null || !balance)
    return [];
  return overdrawnLocationIds(snapshot, balance.category, location =>
    locationBalanceAfterDelete({ index: current, location, snapshot })?.after ?? null);
});

/** Current subtotal of each location, the most a split row may remove from it. */
const locationCaps = computed<Record<string, BigNumber>>(() => {
  const balance = get(removed);
  // Liabilities aren't capped (removing them adds value back).
  if (!balance || isLiability(balance.category))
    return {};
  return Object.fromEntries(
    snapshot.locationDataSnapshot
      .filter(item => item.location !== TOTAL_LOCATION)
      .map(item => [item.location, item.usdValue]),
  );
});

const preview = computed<LocationBalancePreview | null>(() => {
  const current = get(index);
  const target = get(location);
  if (current === null || !target)
    return null;
  return locationBalanceAfterDelete({ index: current, location: target, snapshot });
});

/**
 * Preselect a venue when exactly one can cover the removal — both the lone-location
 * case and the case where only one of several holds enough value. Leaves it empty
 * when several qualify (the user must choose) or none can (they must split).
 */
function preselectLocation(target: number): string {
  const balance = snapshot.balancesSnapshot[target];
  if (!balance)
    return '';
  const overdrawn = overdrawnLocationIds(snapshot, balance.category, location =>
    locationBalanceAfterDelete({ index: target, location, snapshot })?.after ?? null);
  return soleEligibleLocation(get(existingLocations), overdrawn) ?? '';
}

const confirmDisabled = computed<boolean>(() => {
  if (get(splitMode))
    return !get(splitValid);
  const target = get(location);
  return !target || get(disabledLocations).includes(target);
});

function open(target: number): void {
  set(splitMode, false);
  set(splits, []);
  set(splitValid, false);
  set(index, target);
  set(location, preselectLocation(target));
}

function cancel(): void {
  set(index, null);
}

function confirm(): void {
  const current = get(index);
  if (current === null || get(confirmDisabled))
    return;
  emit('confirm', { index: current, location: get(splitMode) ? get(splits) : get(location) });
  cancel();
}

defineExpose({ open });
</script>

<template>
  <ConfirmDialog
    :display="display"
    :title="t('dashboard.snapshot.edit.dialog.balances.delete_title')"
    :message="t('dashboard.snapshot.edit.dialog.balances.delete_confirmation')"
    max-width="700"
    :disabled="confirmDisabled"
    @cancel="cancel()"
    @confirm="confirm()"
  >
    <div class="mt-4 flex flex-col gap-3">
      <!-- Pinned at the top so toggling split mode doesn't make this control jump
        upwards when the single-location selector below it unmounts. -->
      <RuiSwitch
        v-model="splitMode"
        color="primary"
        size="sm"
        hide-details
        data-testid="snapshot-balances-delete-split-toggle"
      >
        {{ t('dashboard.snapshot.detail.split.title') }}
      </RuiSwitch>

      <EditBalancesSnapshotLocationSelector
        v-if="!splitMode"
        v-model="location"
        :disabled-locations="disabledLocations"
        :locations="existingLocations"
        :preview-location-balance="preview"
        :timestamp="timestamp"
      />

      <SnapshotLocationSplit
        v-if="splitMode"
        v-model="splits"
        v-model:valid="splitValid"
        :total="total"
        :locations="existingLocations"
        :max-per-location="locationCaps"
        :timestamp="timestamp"
      />
    </div>
  </ConfirmDialog>
</template>
