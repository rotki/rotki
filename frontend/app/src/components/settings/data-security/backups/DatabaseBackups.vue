<script setup lang="ts">
import { displayDateFormatter } from '@/data/date-formatter';
import { size } from '@/utils/data';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { UserDbBackup, UserDbBackupWithId } from '@/types/backup';

const props = withDefaults(
  defineProps<{
    items: UserDbBackupWithId[];
    selected: UserDbBackupWithId[];
    loading?: boolean;
    directory: string;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  (e: 'update:selected', backup: UserDbBackupWithId[]): void;
  (e: 'remove', backup: UserDbBackupWithId): void;
}>();

const { t } = useI18n();

const sort = ref<DataTableSortData<UserDbBackupWithId>>({
  column: 'size',
  direction: 'desc',
});

const selection = computed({
  get() {
    return props.selected.map(x => x.id);
  },
  set(value?: number[]) {
    if (!value)
      return [];

    emit(
      'update:selected',
      props.items.filter(x => value.includes(x.id)),
    );
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
    key: 'size',
    align: 'end',
    label: t('database_backups.column.size'),
    sortable: true,
  },
  {
    key: 'actions',
    align: 'end',
    sortable: false,
    label: '',
  },
]);

const { items, directory } = toRefs(props);
const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());

const totalSize = computed(() => size(get(items).reduce((sum, db) => sum + db.size, 0)));

const { fileUrl } = useBackupApi();
const getLink = (db: UserDbBackup) => fileUrl(getFilepath(db, directory));

const { show } = useConfirmStore();

function showDeleteConfirmation(item: UserDbBackupWithId) {
  const messageInfo = () => {
    if (item) {
      return {
        size: size(item.size),
        date: displayDateFormatter.format(new Date(item.time * 1000), get(dateDisplayFormat)),
      };
    }

    return {
      size: 0,
      date: 0,
    };
  };

  show(
    {
      title: t('database_backups.confirm.title'),
      message: t('database_backups.confirm.message', { ...messageInfo() }),
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
              name="delete-bin-line"
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
              name="file-download-line"
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
