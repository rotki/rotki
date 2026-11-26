<script setup lang="ts">
import { RuiAlert } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { onKeyStroke } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { definePage } from 'vue-router/experimental';
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import ExportSnapshotDialog from '@/modules/dashboard/ExportSnapshotDialog.vue';
import SnapshotBalancesTable from '@/modules/dashboard/snapshots/components/SnapshotBalancesTable.vue';
import SnapshotEditorToolbar from '@/modules/dashboard/snapshots/components/SnapshotEditorToolbar.vue';
import SnapshotLocationsDrawer from '@/modules/dashboard/snapshots/components/SnapshotLocationsDrawer.vue';
import SnapshotSummary from '@/modules/dashboard/snapshots/components/SnapshotSummary.vue';
import {
  type Filters,
  isolateZeroValue,
  revealExcluded,
} from '@/modules/dashboard/snapshots/composables/snapshot-balance-filter';
import { useSnapshotEditorSession } from '@/modules/dashboard/snapshots/composables/use-snapshot-editor-session';
import { useSnapshotList } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { useSnapshotNeighbours } from '@/modules/dashboard/snapshots/composables/use-snapshot-neighbours';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.statistics_sub.snapshots'), icon: 'lu-camera', searchable: false },
    canNavigateBack: true,
    noteLocation: NoteLocation.STATISTICS_SNAPSHOTS,
  },
});

const { t } = useI18n({ useScope: 'global' });
const route = useRoute<'/statistics/snapshots/[timestamp]'>();

const timestamp = computed<number>(() => Number(String(get(route).params.timestamp)));

const exportDialog = ref<boolean>(false);
const locationsDrawer = ref<boolean>(false);
const balanceFilters = ref<Filters>({});

/**
 * `rows`, and the prev/next order and deltas derived from them, come from the cached net-value
 * series. `refreshNetValue` re-pulls it, so a save or delete here reaches this page's navigation
 * and the list page alike, both reading the same store.
 */
const { refresh: refreshNetValue, rows } = useSnapshotList();

const {
  addBalance,
  addLocation,
  canUndo,
  changes,
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
  loadError,
  loading,
  mismatch,
  modelActionError: actionError,
  modelSaveSuccess: saveSuccess,
  netWorth,
  performDelete,
  reconcileLocations,
  save,
  saving,
  undo,
} = useSnapshotEditorSession({ refreshNetValue, timestamp });

const { hasNext, hasPrev, navigate, previous } = useSnapshotNeighbours({ rows, timestamp });

/** Sweeps the valueless balances the table flagged, without asking: the draft's undo restores them. */
function bulkDelete(indices: number[]): void {
  if (indices.length > 0)
    deleteBalances(indices);
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
    class="container"
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
        @delete="performDelete()"
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
        @remove-balances="deleteBalances($event)"
        @show-excluded="balanceFilters = revealExcluded(balanceFilters)"
        @show-zero-value="balanceFilters = isolateZeroValue(balanceFilters)"
      />

      <SnapshotBalancesTable
        v-model:filters="balanceFilters"
        :snapshot="draft"
        :timestamp="timestamp"
        :locked="!!mismatch"
        @add="addBalance($event)"
        @edit="editBalance($event.index, $event.mutation)"
        @delete="deleteBalance($event.index, $event.location, $event.markSpam)"
        @bulk-delete="bulkDelete($event)"
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
      :balance="netWorth"
    />
  </div>
</template>
