<script setup lang="ts">
import type { Snapshot } from '@/modules/dashboard/snapshots';
import type { BalanceDeletion } from '@/modules/dashboard/snapshots/composables/use-snapshot-draft';
import type { LocationSplit } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { type BigNumber, Zero } from '@rotki/common';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import EditBalancesSnapshotLocationSelector from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotLocationSelector.vue';
import SnapshotLocationSplit from '@/modules/dashboard/snapshots/components/SnapshotLocationSplit.vue';
import { SnapshotSpamEligibility, useSnapshotSpamEligibility } from '@/modules/dashboard/snapshots/composables/use-snapshot-spam-eligibility';
import { locationBalanceAfterDelete, type LocationBalancePreview, overdrawnLocationIds, soleEligibleLocation } from '@/modules/dashboard/snapshots/utils/snapshot-location-balance';
import { isLiability, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';

const { snapshot, timestamp } = defineProps<{
  snapshot: Snapshot;
  timestamp: number;
}>();

const emit = defineEmits<{
  confirm: [payload: BalanceDeletion];
}>();

const { t } = useI18n({ useScope: 'global' });

const { getAssetField } = useAssetInfoRetrieval();
const { spamEligibility } = useSnapshotSpamEligibility();

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

/** Whether the row can be removed with its asset marked as spam, computed while the dialog is open. */
const spamOption = computed<SnapshotSpamEligibility>(() => {
  const balance = get(removed);
  return balance ? spamEligibility(balance.assetIdentifier) : SnapshotSpamEligibility.UNAVAILABLE;
});

const canMarkSpam = computed<boolean>(() => get(spamOption) === SnapshotSpamEligibility.ELIGIBLE);

/** Label of the "delete and mark as spam" button, or null when the row does not offer it. */
const spamAction = computed<string | null>(() =>
  get(spamOption) === SnapshotSpamEligibility.UNAVAILABLE ? null : t('dashboard.snapshot.edit.dialog.balances.spam.action'));

const spamDisabledReason = computed<string | null>(() =>
  get(spamOption) === SnapshotSpamEligibility.MANUAL_BALANCE ? t('dashboard.snapshot.edit.dialog.balances.spam.manual_balance') : null);

const removedSymbol = computed<string>(() => {
  const balance = get(removed);
  return balance ? getAssetField(balance.assetIdentifier, 'symbol') || balance.assetIdentifier : '';
});

/** The other rows of the removed asset, which stay in the snapshot and are hidden as spam once saved. */
const otherRowsOfAsset = computed<number>(() => {
  const current = get(index);
  const balance = get(removed);
  if (current === null || !balance)
    return 0;
  return snapshot.balancesSnapshot.filter((item, position) =>
    position !== current && item.assetIdentifier === balance.assetIdentifier).length;
});

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

/**
 * Removes the row, debiting the chosen location or split.
 *
 * @param markSpam - also mark the row's asset as spam on save; ignored unless the asset is eligible
 */
function confirm(markSpam: boolean = false): void {
  const current = get(index);
  if (current === null || get(confirmDisabled) || (markSpam && !get(canMarkSpam)))
    return;
  emit('confirm', { index: current, location: get(splitMode) ? get(splits) : get(location), markSpam });
  cancel();
}

defineExpose({ open });
</script>

<template>
  <ConfirmDialog
    :display="display"
    :title="t('dashboard.snapshot.edit.dialog.balances.delete_title')"
    :message="t('dashboard.snapshot.edit.dialog.balances.delete_confirmation')"
    :primary-action="t('common.actions.delete')"
    :alternative-action="spamAction"
    :alternative-disabled-reason="spamDisabledReason"
    confirm-type="warning"
    max-width="700"
    :disabled="confirmDisabled"
    @cancel="cancel()"
    @confirm="confirm()"
    @alternative="confirm(true)"
  >
    <div class="mt-4 flex flex-col gap-3">
      <RuiSwitch
        v-model="splitMode"
        color="primary"
        size="sm"
        details="hidden"
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
        untitled
        :total="total"
        :locations="existingLocations"
        :max-per-location="locationCaps"
        :timestamp="timestamp"
      />

      <RuiAlert
        v-if="canMarkSpam"
        type="warning"
        data-testid="snapshot-balances-delete-spam-warning"
      >
        <div class="font-medium">
          {{ t('dashboard.snapshot.edit.dialog.balances.spam.title', { symbol: removedSymbol }) }}
        </div>
        <ul class="list-disc ps-5">
          <li>{{ t('dashboard.snapshot.edit.dialog.balances.spam.effects.not_queried') }}</li>
          <li>{{ t('dashboard.snapshot.edit.dialog.balances.spam.effects.hidden') }}</li>
          <li>{{ t('dashboard.snapshot.edit.dialog.balances.spam.effects.net_worth') }}</li>
          <li>{{ t('dashboard.snapshot.edit.dialog.balances.spam.effects.on_save') }}</li>
        </ul>
        <div
          v-if="otherRowsOfAsset > 0"
          class="mt-1"
          data-testid="snapshot-balances-delete-spam-other-rows"
        >
          {{ t('dashboard.snapshot.edit.dialog.balances.spam.other_rows', { count: otherRowsOfAsset }, otherRowsOfAsset) }}
        </div>
      </RuiAlert>
    </div>
  </ConfirmDialog>
</template>
