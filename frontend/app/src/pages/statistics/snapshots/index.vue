<script setup lang="ts">
import type { TablePaginationData } from '@rotki/ui-library';
import type { LocationQueryRaw } from 'vue-router';
import type { LocationQuery } from '@/modules/core/table/route';
import { type BigNumber, type Message, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { NoteLocation } from '@/modules/core/common/notes';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { applyPaginationDefaults, parseQueryPagination } from '@/modules/core/table/pagination-filter-utils';
import ExportSnapshotDialog from '@/modules/dashboard/ExportSnapshotDialog.vue';
import SnapshotImportDialog from '@/modules/dashboard/SnapshotImportDialog.vue';
import SnapshotListFilter from '@/modules/dashboard/snapshots/components/SnapshotListFilter.vue';
import SnapshotListTable from '@/modules/dashboard/snapshots/components/SnapshotListTable.vue';
import { useSnapshotActions } from '@/modules/dashboard/snapshots/composables/use-snapshot-actions';
import { type SnapshotListFilters, type SnapshotListRow, useSnapshotList } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.statistics_sub.snapshots'), icon: 'lu-camera', parent: '/statistics/', order: 30, drawer: 'statistics-snapshots' },
    noteLocation: NoteLocation.STATISTICS_SNAPSHOTS,
  },
});

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();
const itemsPerPage = useItemsPerPage();

const exportDialog = ref<boolean>(false);
const importDialog = ref<boolean>(false);
const selectedTimestamp = ref<number>(0);

// View-state lives in the URL query, so it survives reload and is restored by the
// browser's back/forward when returning from a snapshot's detail page.
const filters = ref<SnapshotListFilters>({});
const pagination = ref<TablePaginationData>(applyPaginationDefaults(get(itemsPerPage)));

const { hasSnapshots, loading, refresh, rows } = useSnapshotList(filters);
const { deleteSnapshot } = useSnapshotApi();
const { setMessage } = useMessageStore();
const { show } = useConfirmStore();
const { forceSave, forceSaving, importing, importSnapshot, modelBalanceFile, modelLocationFile } = useSnapshotActions();

/** Reads the date range + page from the URL query into the view-state. */
function readQuery(query: LocationQuery): void {
  const from = Number(query.from);
  const to = Number(query.to);
  set(filters, {
    fromTimestamp: query.from && Number.isFinite(from) ? from : undefined,
    toTimestamp: query.to && Number.isFinite(to) ? to : undefined,
  });
  set(pagination, parseQueryPagination(query, get(pagination)));
}

/** Mirrors the view-state back into the URL query (replace: no history spam). */
function writeQuery(): void {
  const { fromTimestamp, toTimestamp } = get(filters);
  const { limit, page } = get(pagination);
  const query: LocationQueryRaw = {
    ...(fromTimestamp !== undefined ? { from: fromTimestamp } : {}),
    ...(toTimestamp !== undefined ? { to: toTimestamp } : {}),
    ...(page > 1 ? { page } : {}),
    ...(limit !== get(itemsPerPage) ? { limit } : {}),
  };
  startPromise(router.replace({ query }));
}

readQuery(get(route).query);

watch([
  (): number | undefined => get(filters).fromTimestamp,
  (): number | undefined => get(filters).toTimestamp,
  (): number => get(pagination).page,
  (): number => get(pagination).limit,
], writeQuery);

// When the list is empty, tell apart a genuinely empty account from a range
// filter that excludes everything.
const emptyDescription = computed<string>(() =>
  get(hasSnapshots)
    ? t('dashboard.snapshot.list.empty_filtered')
    : t('dashboard.snapshot.list.empty'));

function open(timestamp: number): void {
  startPromise(router.push(`/statistics/snapshots/${timestamp}`));
}

// The export dialog shows the selected snapshot's stored USD net worth; the dialog
// converts it at the snapshot's historic rate itself (#12277), lazily, so opening
// it never triggers a whole-series conversion.
const selectedRow = computed<SnapshotListRow | undefined>(() =>
  get(rows).find(item => item.timestamp === get(selectedTimestamp)));
const selectedBalance = computed<BigNumber>(() => get(selectedRow)?.usdValue ?? Zero);

function openExport(timestamp: number): void {
  set(selectedTimestamp, timestamp);
  set(exportDialog, true);
}

async function performDelete(timestamp: number): Promise<void> {
  let message: Message;
  try {
    const success = await deleteSnapshot({ timestamp });
    message = {
      description: success
        ? t('dashboard.snapshot.delete.message.success')
        : t('dashboard.snapshot.delete.message.failure'),
      success,
      title: t('dashboard.snapshot.delete.message.title'),
    };
    if (success)
      await refresh();
  }
  catch (error: unknown) {
    message = {
      description: getErrorMessage(error),
      success: false,
      title: t('dashboard.snapshot.delete.message.title'),
    };
  }
  setMessage(message);
}

function confirmDelete(timestamp: number): void {
  show(
    {
      message: t('dashboard.snapshot.delete.dialog.message'),
      title: t('dashboard.snapshot.delete.dialog.title'),
    },
    () => performDelete(timestamp),
  );
}

// Force-save refetches every balance (slow, rate-limit prone), so confirm first.
function confirmTakeSnapshot(): void {
  show(
    {
      message: t('dashboard.snapshot.list.take_snapshot_confirm.message'),
      title: t('dashboard.snapshot.list.take_snapshot_confirm.title'),
    },
    () => forceSave(),
  );
}
</script>

<template>
  <TablePageLayout :title="[t('dashboard.snapshot.list.title')]">
    <template #buttons>
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="loading"
        @click="refresh()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-cw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>

      <SnapshotImportDialog
        v-model="importDialog"
        v-model:balance-file="modelBalanceFile"
        v-model:location-file="modelLocationFile"
        :loading="importing"
        @import="importSnapshot()"
      />

      <RuiTooltip
        :open-delay="400"
        tooltip-class="max-w-[16rem]"
      >
        <template #activator>
          <RuiButton
            color="primary"
            :loading="forceSaving"
            @click="confirmTakeSnapshot()"
          >
            <template #prepend>
              <RuiIcon name="lu-camera" />
            </template>
            {{ t('dashboard.snapshot.list.take_snapshot') }}
          </RuiButton>
        </template>
        {{ t('snapshot_action_button.snapshot_tooltip') }}
      </RuiTooltip>
    </template>

    <RuiCard>
      <SnapshotListFilter
        v-model="filters"
        class="mb-4"
      />

      <SnapshotListTable
        v-model:pagination="pagination"
        :rows="rows"
        :loading="loading"
        :empty-description="emptyDescription"
        @open="open($event)"
        @export="openExport($event)"
        @delete="confirmDelete($event)"
      />
    </RuiCard>

    <ExportSnapshotDialog
      v-model="exportDialog"
      :timestamp="selectedTimestamp"
      :balance="selectedBalance"
    />
  </TablePageLayout>
</template>
