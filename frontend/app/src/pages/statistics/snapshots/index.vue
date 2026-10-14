<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import TableFrame from '@/modules/core/table/TableFrame.vue';
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

const confirmOpen = ref<boolean>(false);

const {
  confirmDelete,
  emptyDescription,
  exporting,
  exportSnapshot,
  forceSaving,
  importing,
  importSnapshot,
  loading,
  modelBalanceFile,
  modelFilters,
  modelImportDialog,
  modelLocationFile,
  modelPagination,
  open,
  refresh,
  rows,
  takeSnapshot,
} = useSnapshotsPage();

async function confirmTakeSnapshot(): Promise<void> {
  set(confirmOpen, false);
  await takeSnapshot();
}
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.statistics'), t('dashboard.snapshot.list.title')]">
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

      <RuiMenu
        v-model="confirmOpen"
        role="dialog"
        :class-names="{ menu: 'w-80' }"
        :options="{ placement: 'bottom-end' }"
      >
        <template #activator="{ attrs }">
          <RuiButton
            v-bind="attrs"
            color="primary"
            :loading="forceSaving"
            data-testid="take-snapshot"
          >
            <template #prepend>
              <RuiIcon name="lu-camera" />
            </template>
            {{ t('dashboard.snapshot.list.take_snapshot') }}
          </RuiButton>
        </template>
        <div
          class="flex flex-col gap-3 p-4"
          data-testid="take-snapshot-confirm"
        >
          <p class="text-sm text-rui-text-secondary">
            {{ t('dashboard.snapshot.list.take_snapshot_confirm.message') }}
          </p>
          <div class="flex justify-end gap-2">
            <RuiButton
              variant="text"
              color="primary"
              size="sm"
              data-testid="take-snapshot-cancel"
              @click="confirmOpen = false"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>
            <RuiButton
              color="primary"
              size="sm"
              data-testid="take-snapshot-confirm-button"
              @click="confirmTakeSnapshot()"
            >
              {{ t('dashboard.snapshot.list.take_snapshot') }}
            </RuiButton>
          </div>
        </div>
      </RuiMenu>
    </template>

    <TableFrame>
      <template #toolbar>
        <SnapshotListFilter
          v-model="modelFilters"
          class="flex-1 min-w-64"
        />
      </template>

      <SnapshotListTable
        v-model:pagination="modelPagination"
        :rows="rows"
        :loading="loading"
        :empty-description="emptyDescription"
        :exporting="exporting"
        @open="open($event)"
        @export="exportSnapshot($event)"
        @delete="confirmDelete($event)"
      />
    </TableFrame>
  </TablePageLayout>
</template>
