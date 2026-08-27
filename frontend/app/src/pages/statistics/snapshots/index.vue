<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import ExportSnapshotDialog from '@/modules/dashboard/ExportSnapshotDialog.vue';
import SnapshotImportDialog from '@/modules/dashboard/SnapshotImportDialog.vue';
import SnapshotListFilter from '@/modules/dashboard/snapshots/components/SnapshotListFilter.vue';
import SnapshotListTable from '@/modules/dashboard/snapshots/components/SnapshotListTable.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useSnapshotsPage } from '@/pages/statistics/snapshots/use-snapshots-page';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.statistics_sub.snapshots'), icon: 'lu-camera', parent: '/statistics/', order: 30, drawer: 'statistics-snapshots' },
    noteLocation: NoteLocation.STATISTICS_SNAPSHOTS,
  },
});

const { t } = useI18n({ useScope: 'global' });

const {
  confirmDelete,
  confirmTakeSnapshot,
  emptyDescription,
  forceSaving,
  importing,
  importSnapshot,
  loading,
  modelBalanceFile,
  modelExportDialog,
  modelFilters,
  modelImportDialog,
  modelLocationFile,
  modelPagination,
  open,
  openExport,
  refresh,
  rows,
  selectedBalance,
  selectedTimestamp,
} = useSnapshotsPage();
</script>

<template>
  <TablePageLayout :title="[t('dashboard.snapshot.list.title')]">
    <template #buttons>
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="loading"
        data-testid="refresh-snapshots"
        @click="refresh()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-cw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>

      <SnapshotImportDialog
        v-model="modelImportDialog"
        v-model:balance-file="modelBalanceFile"
        v-model:location-file="modelLocationFile"
        :loading="importing"
        @import="importSnapshot()"
      />

      <RuiTooltip
        :open-delay="400"
        :class-names="{ tooltip: 'max-w-[16rem]' }"
      >
        <template #activator>
          <RuiButton
            color="primary"
            :loading="forceSaving"
            data-testid="take-snapshot"
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
        v-model="modelFilters"
        class="mb-4"
      />

      <SnapshotListTable
        v-model:pagination="modelPagination"
        :rows="rows"
        :loading="loading"
        :empty-description="emptyDescription"
        @open="open($event)"
        @export="openExport($event)"
        @delete="confirmDelete($event)"
      />
    </RuiCard>

    <ExportSnapshotDialog
      v-model="modelExportDialog"
      :timestamp="selectedTimestamp"
      :balance="selectedBalance"
    />
  </TablePageLayout>
</template>
