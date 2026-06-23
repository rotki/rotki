<script setup lang="ts">
import type { Snapshot } from '@/modules/dashboard/snapshots';
import { type BigNumber, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { NoteLocation } from '@/modules/core/common/notes';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import ExportSnapshotDialog from '@/modules/dashboard/ExportSnapshotDialog.vue';
import SnapshotBalancesTable from '@/modules/dashboard/snapshots/components/SnapshotBalancesTable.vue';
import SnapshotEditorToolbar from '@/modules/dashboard/snapshots/components/SnapshotEditorToolbar.vue';
import SnapshotLocationsDrawer from '@/modules/dashboard/snapshots/components/SnapshotLocationsDrawer.vue';
import SnapshotSummary from '@/modules/dashboard/snapshots/components/SnapshotSummary.vue';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';
import { useSnapshotDraft } from '@/modules/dashboard/snapshots/composables/use-snapshot-draft';
import { useSnapshotList } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { useSnapshotStore } from '@/modules/dashboard/snapshots/use-snapshot-store';
import { convertUsdToFiat } from '@/modules/dashboard/snapshots/utils/snapshot-fx';
import { getTotalValue } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.STATISTICS_SNAPSHOTS,
  },
  name: 'statistics-snapshot-detail',
});

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const timestamp = computed<number>(() => Number(String(get(route).params.timestamp)));

const loading = ref<boolean>(true);
const saving = ref<boolean>(false);
const loadError = ref<string>();
const actionError = ref<string>();
const saveSuccess = ref<boolean>(false);
const loaded = ref<Snapshot>();
const exportDialog = ref<boolean>(false);
const locationsDrawer = ref<boolean>(false);

const { fetchSnapshot, persist, remove } = useSnapshotStore();
// `rows` (and the prev/next order + deltas derived from them) come from the cached
// net-value series; `refreshNetValue` re-pulls it so a save/delete here is
// reflected in this page's navigation and in the list page (shared store state).
const { refresh: refreshNetValue, rows } = useSnapshotList();
const { show } = useConfirmStore();

const {
  addBalance,
  addLocation,
  canUndo,
  changes,
  commit,
  deleteBalance,
  deleteBalances,
  deleteLocation,
  discard,
  distributeLocations,
  draft,
  editBalance,
  editLocation,
  excludeNfts,
  isDirty,
  mismatch,
  reconcileLocations,
  undo,
} = useSnapshotDraft(loaded);

const { isUsd, loading: rateLoading, rate } = useHistoricFiatConversion(timestamp);

const netWorth = computed<BigNumber>(() => {
  const current = get(draft);
  return current ? getTotalValue(current.locationDataSnapshot) : Zero;
});

const exportBalance = computed<BigNumber>(() => {
  const value = get(netWorth);
  return get(isUsd) ? value : convertUsdToFiat(value, get(rate));
});

// Mirror the list view: show a skeleton in the export dialog while the historic
// rate is still resolving instead of a misleading converted-from-zero balance.
const exportBalanceLoading = computed<boolean>(() => !get(isUsd) && get(rateLoading));

/** Snapshot timestamps oldest-first, used for prev/next navigation + the delta. */
const orderedTimestamps = computed<number[]>(() => get(rows).map(row => row.timestamp).sort((a, b) => a - b));
const currentIndex = computed<number>(() => get(orderedTimestamps).indexOf(get(timestamp)));
const hasPrev = computed<boolean>(() => get(currentIndex) > 0);
const hasNext = computed<boolean>(() => {
  const index = get(currentIndex);
  return index > -1 && index < get(orderedTimestamps).length - 1;
});

const previousTimestamp = computed<number | undefined>(() => {
  const index = get(currentIndex);
  return index > 0 ? get(orderedTimestamps)[index - 1] : undefined;
});

const previous = computed<{ value: BigNumber; timestamp: number } | undefined>(() => {
  const ts = get(previousTimestamp);
  if (ts === undefined)
    return undefined;
  const value = get(rows).find(row => row.timestamp === ts)?.usdValue;
  return value !== undefined ? { timestamp: ts, value } : undefined;
});

async function load(): Promise<void> {
  // Only show the full-page loader on the first load. On prev/next navigation the
  // current snapshot stays on screen and updates in place once the next one
  // arrives, so the near-identical layout doesn't flash through ProgressScreen.
  if (!get(loaded))
    set(loading, true);
  set(loadError, undefined);
  try {
    set(loaded, await fetchSnapshot(get(timestamp)));
  }
  catch (error: unknown) {
    set(loadError, getErrorMessage(error));
  }
  finally {
    set(loading, false);
  }
}

watch(timestamp, load, { immediate: true });

function navigate(direction: 'prev' | 'next'): void {
  const target = get(orderedTimestamps)[get(currentIndex) + (direction === 'next' ? 1 : -1)];
  if (target !== undefined)
    startPromise(router.push(`/statistics/snapshots/${target}`));
}

async function save(): Promise<void> {
  set(saving, true);
  set(actionError, undefined);
  try {
    const success = await commit(snapshot => persist(get(timestamp), snapshot));
    if (success) {
      set(saveSuccess, true);
      // The edited total changes this snapshot's point in the net-value series,
      // which drives the list, prev/next order and deltas — re-pull it so they
      // don't keep showing the pre-edit value.
      await refreshNetValue();
    }
    else {
      set(actionError, t('dashboard.snapshot.detail.save.failure'));
    }
  }
  catch (error: unknown) {
    set(actionError, getErrorMessage(error));
  }
  finally {
    set(saving, false);
  }
}

async function performDelete(): Promise<void> {
  set(actionError, undefined);
  try {
    const success = await remove(get(timestamp));
    if (success) {
      // Drop this snapshot from the net-value series before returning, so the
      // list doesn't still show the just-deleted row (it only auto-fetches when
      // the series is empty).
      await refreshNetValue();
      await router.push('/statistics/snapshots');
      return;
    }
    set(actionError, t('dashboard.snapshot.delete.message.failure'));
  }
  catch (error: unknown) {
    set(actionError, getErrorMessage(error));
  }
}

function confirmDelete(): void {
  show(
    {
      message: t('dashboard.snapshot.delete.dialog.message'),
      title: t('dashboard.snapshot.delete.dialog.title'),
    },
    () => performDelete(),
  );
}

/** Confirm before sweeping the valueless balances the table flagged for removal. */
function confirmBulkDelete(indices: number[]): void {
  if (indices.length === 0)
    return;
  show(
    {
      message: t('dashboard.snapshot.detail.balances.bulk_delete.message', { count: indices.length }, indices.length),
      title: t('dashboard.snapshot.detail.balances.bulk_delete.title'),
    },
    () => deleteBalances(indices),
  );
}

/** Whether keyboard focus sits in a field, so shortcuts shouldn't hijack keys. */
function inEditableField(): boolean {
  const element = document.activeElement;
  if (!(element instanceof HTMLElement))
    return false;
  return ['INPUT', 'SELECT', 'TEXTAREA'].includes(element.tagName) || element.isContentEditable;
}

onKeyStroke(['ArrowLeft'], (event) => {
  if (!inEditableField() && get(hasPrev)) {
    event.preventDefault();
    navigate('prev');
  }
});

onKeyStroke(['ArrowRight'], (event) => {
  if (!inEditableField() && get(hasNext)) {
    event.preventDefault();
    navigate('next');
  }
});

onKeyStroke(['s', 'S'], (event) => {
  if (!(event.metaKey || event.ctrlKey))
    return;
  event.preventDefault();
  if (get(isDirty) && !get(saving))
    startPromise(save());
});

onKeyStroke(['z', 'Z'], (event) => {
  if (!(event.metaKey || event.ctrlKey) || inEditableField())
    return;
  event.preventDefault();
  if (get(canUndo))
    undo();
});

watch(isDirty, (dirty) => {
  if (dirty)
    set(saveSuccess, false);
});

// Guard against leaving with unsaved changes (covers prev/next + outbound nav).
onBeforeRouteLeave(() => {
  if (!get(isDirty))
    return true;

  return new Promise<boolean>((resolve) => {
    show(
      {
        message: t('dashboard.snapshot.detail.leave.message'),
        title: t('dashboard.snapshot.detail.leave.title'),
      },
      () => resolve(true),
      () => resolve(false),
    );
  });
});

// The route guard above only covers in-app navigation; a browser refresh, tab
// close or Electron window close bypasses it. Fall back to the native prompt.
useEventListener(window, 'beforeunload', (event: BeforeUnloadEvent) => {
  if (!get(isDirty))
    return;
  event.preventDefault();
  // Legacy Chromium requires a returnValue to trigger the prompt.
  event.returnValue = '';
});
</script>

<template>
  <ProgressScreen v-if="loading">
    {{ t('dashboard.snapshot.detail.loading') }}
  </ProgressScreen>

  <div
    v-else-if="loadError"
    class="container"
  >
    <RuiAlert
      type="error"
      :title="t('dashboard.snapshot.detail.not_found')"
    >
      {{ t('dashboard.snapshot.detail.load_error', { message: loadError }) }}
    </RuiAlert>
  </div>

  <div
    v-else-if="draft"
    class="container py-4"
  >
    <div class="flex flex-col gap-4">
      <SnapshotEditorToolbar
        :timestamp="timestamp"
        :changes="changes"
        :can-undo="canUndo"
        :saving="saving"
        :has-prev="hasPrev"
        :has-next="hasNext"
        @save="save()"
        @discard="discard()"
        @undo="undo()"
        @export="exportDialog = true"
        @delete="confirmDelete()"
        @navigate="navigate($event)"
      />

      <RuiAlert
        v-if="actionError"
        type="error"
        closeable
        data-testid="snapshot-action-error"
        @close="actionError = undefined"
      >
        {{ actionError }}
      </RuiAlert>

      <RuiAlert
        v-else-if="saveSuccess"
        type="success"
        closeable
        data-testid="snapshot-save-success"
        @close="saveSuccess = false"
      >
        {{ t('dashboard.snapshot.detail.save.success') }}
      </RuiAlert>

      <SnapshotSummary
        v-model:exclude-nfts="excludeNfts"
        :snapshot="draft"
        :timestamp="timestamp"
        :mismatch="mismatch"
        :previous="previous"
        @edit-locations="locationsDrawer = true"
        @reconcile-locations="reconcileLocations($event)"
      />

      <SnapshotBalancesTable
        :snapshot="draft"
        :timestamp="timestamp"
        :locked="!!mismatch"
        @add="addBalance($event)"
        @edit="editBalance($event.index, $event.mutation)"
        @delete="deleteBalance($event.index, $event.location)"
        @bulk-delete="confirmBulkDelete($event)"
      />
    </div>

    <SnapshotLocationsDrawer
      v-model="locationsDrawer"
      :snapshot="draft"
      :timestamp="timestamp"
      @add="addLocation($event)"
      @edit="editLocation($event.index, $event.location)"
      @delete="deleteLocation($event)"
      @distribute="distributeLocations($event)"
    />

    <ExportSnapshotDialog
      v-model="exportDialog"
      :timestamp="timestamp"
      :balance="exportBalance"
      :loading="exportBalanceLoading"
    />
  </div>
</template>
