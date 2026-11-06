<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { UserDbBackup, UserDbBackupWithId } from '@/modules/session/backup';
import { size } from '@/modules/core/common/data/data';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { getFilepath } from '@/modules/core/common/file/file';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useBackupApi } from '@/modules/session/api/use-backup-api';
import { useSetting } from '@/modules/settings/use-setting';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';

const selected = defineModel<UserDbBackupWithId[]>('selected', { required: true });

const { directory, items, loading = false, selectionMode = false } = defineProps<{
  items: UserDbBackupWithId[];
  loading?: boolean;
  directory: string;
  /** Whether the user switched on selecting rows; the checkbox column only shows while it is on. */
  selectionMode?: boolean;
}>();

const emit = defineEmits<{
  /** Emitted only once the user accepted the question the row's delete button asks. */
  remove: [backup: UserDbBackupWithId];
}>();

const { t } = useI18n({ useScope: 'global' });

const sort = ref<DataTableSortData<UserDbBackupWithId>>({
  column: 'size',
  direction: 'desc',
});

/** `undefined` outside selection mode, which is what makes the table drop its checkbox column. */
const selection = computed<number[] | undefined>({
  get() {
    if (!selectionMode)
      return undefined;

    return get(selected).map(x => x.id);
  },
  set(value?: number[]) {
    if (!value) {
      set(selected, []);
      return;
    }

    set(selected, items.filter(x => value.includes(x.id)));
  },
});

const tableHeaders = computed<DataTableColumn<UserDbBackupWithId>[]>(() => [
  {
    key: 'version',
    label: t('database_backups.column.version'),
    sortable: true,
  },
  {
    key: 'time',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'size',
    label: t('database_backups.column.size'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'actions',
    label: '',
    sortable: false,
  },
]);

useRememberTableSorting<UserDbBackupWithId>(TableId.USER_DB_BACKUP, sort, tableHeaders);

const dateDisplayFormat = useSetting('dateDisplayFormat');

const totalSize = computed(() => size(items.reduce((sum, db) => sum + db.size, 0)));

const { fileUrl } = useBackupApi();
const getLink = (db: UserDbBackup) => fileUrl(getFilepath(db, directory));

/** What a row's delete button asks, naming the backup by its date and size. */
function deleteMessage(item: UserDbBackupWithId): string {
  return t('database_backups.confirm.message', {
    date: displayDateFormatter.format(new Date(item.time * 1000), get(dateDisplayFormat)),
    size: size(item.size),
  });
}
</script>

<template>
  <RuiDataTable
    v-model="selection"
    v-model:sort="sort"
    :rows="items"
    row-attr="id"
    outlined
    class="bg-white dark:bg-transparent"
    dense
    :cols="tableHeaders"
    :loading="loading"
  >
    <template #item.time="{ row }">
      <DateDisplay :timestamp="row.time" />
    </template>

    <template #item.size="{ row }">
      {{ size(row.size) }}
    </template>

    <template #item.actions="{ row }">
      <ConfirmPopover
        :title="t('database_backups.confirm.title')"
        :message="deleteMessage(row)"
        :confirm-label="t('common.actions.delete')"
        @confirm="emit('remove', row)"
      >
        <template #activator="{ attrs }">
          <RuiTooltip
            :open-delay="400"
            :options="{ placement: 'top' }"
          >
            <template #activator>
              <RuiButton
                variant="text"
                color="primary"
                icon
                data-testid="backup-delete"
                v-bind="attrs"
              >
                <RuiIcon
                  size="16"
                  name="lu-trash-2"
                />
              </RuiButton>
            </template>
            <span>{{ t('database_backups.action.delete') }}</span>
          </RuiTooltip>
        </template>
      </ConfirmPopover>
      <RuiTooltip
        :open-delay="400"
        :options="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            variant="text"
            color="primary"
            icon
            :href="getLink(row)"
            download
            tag="a"
            class="mx-1"
          >
            <RuiIcon
              size="16"
              name="lu-file-down"
            />
          </RuiButton>
        </template>
        <span>{{ t('database_backups.action.download') }}</span>
      </RuiTooltip>
    </template>

    <template #body.append>
      <RowAppend
        :label-colspan="selectionMode ? 3 : 2"
        :label="t('common.total')"
        :right-patch-colspan="1"
      >
        {{ totalSize }}
      </RowAppend>
    </template>
  </RuiDataTable>
</template>
