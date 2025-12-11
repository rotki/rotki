<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { UserDbBackup, UserDbBackupWithId } from '@/types/backup';
import DateDisplay from '@/components/display/DateDisplay.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { useBackupApi } from '@/composables/api/backup';
import { displayDateFormatter } from '@/data/date-formatter';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useConfirmStore } from '@/store/confirm';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { size } from '@/utils/data';
import { getFilepath } from '@/utils/file';

const selected = defineModel<UserDbBackupWithId[]>('selected', { required: true });

const props = withDefaults(
  defineProps<{
    items: UserDbBackupWithId[];
    loading?: boolean;
    directory: string;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  remove: [backup: UserDbBackupWithId];
}>();

const { t } = useI18n({ useScope: 'global' });

const sort = ref<DataTableSortData<UserDbBackupWithId>>({
  column: 'size',
  direction: 'desc',
});

const selection = computed<number[] | undefined>({
  get() {
    return get(selected).map(x => x.id);
  },
  set(value?: number[]) {
    if (!value) {
      set(selected, []);
      return;
    }

    set(selected, props.items.filter(x => value.includes(x.id)));
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

const { directory, items } = toRefs(props);
const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());

const totalSize = computed(() => size(get(items).reduce((sum, db) => sum + db.size, 0)));

const { fileUrl } = useBackupApi();
const getLink = (db: UserDbBackup) => fileUrl(getFilepath(db, directory));

const { show } = useConfirmStore();

function showDeleteConfirmation(item: UserDbBackupWithId) {
  const messageInfo = () => {
    if (item) {
      return {
        date: displayDateFormatter.format(new Date(item.time * 1000), get(dateDisplayFormat)),
        size: size(item.size),
      };
    }

    return {
      date: 0,
      size: 0,
    };
  };

  show(
    {
      message: t('database_backups.confirm.message', { ...messageInfo() }),
      title: t('database_backups.confirm.title'),
    },
    () => emit('remove', item),
  );
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
      <RuiTooltip
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            variant="text"
            color="primary"
            icon
            @click="showDeleteConfirmation(row)"
          >
            <RuiIcon
              size="16"
              name="lu-trash-2"
            />
          </RuiButton>
        </template>
        <span>{{ t('database_backups.action.delete') }}</span>
      </RuiTooltip>
      <RuiTooltip
        :open-delay="400"
        :popper="{ placement: 'top' }"
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
        label-colspan="3"
        class-name="[&>td]:p-4 text-sm"
        :label="t('common.total')"
        :right-patch-colspan="1"
      >
        {{ totalSize }}
      </RowAppend>
    </template>
  </RuiDataTable>
</template>
