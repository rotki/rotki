<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import Fragment from '@/components/helper/Fragment';
import { displayDateFormatter } from '@/data/date_formatter';
import { type UserDbBackup } from '@/types/backup';
import { size } from '@/utils/data';

const props = withDefaults(
  defineProps<{
    items: UserDbBackup[];
    selected: UserDbBackup[];
    loading?: boolean;
    directory: string;
  }>(),
  {
    loading: false
  }
);

const emit = defineEmits<{
  (e: 'change', backup: UserDbBackup[]): void;
  (e: 'remove', backup: UserDbBackup): void;
}>();

const { t } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    value: 'version',
    text: t('database_backups.column.version')
  },
  {
    value: 'time',
    text: t('common.datetime')
  },
  {
    value: 'size',
    align: 'end',
    text: t('database_backups.column.size')
  },
  { value: 'actions', align: 'end', sortable: false, text: '' }
]);

const { items, directory } = toRefs(props);

const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());

const remove = (item: UserDbBackup & { index: number }) => {
  emit('remove', item);
};

const totalSize = computed(() =>
  size(get(items).reduce((sum, db) => sum + db.size, 0))
);

const { fileUrl } = useBackupApi();
const getLink = (db: UserDbBackup) => fileUrl(getFilepath(db, directory));

const onSelectedChange = (selected: UserDbBackup[]) => {
  emit('change', selected);
};

const itemsWithIndex: ComputedRef<(UserDbBackup & { index: number })[]> =
  computed(() =>
    get(items).map((item, index) => ({
      ...item,
      index
    }))
  );

const { show } = useConfirmStore();

const showDeleteConfirmation = (item: UserDbBackup & { index: number }) => {
  const messageInfo = () => {
    if (item) {
      return {
        size: size(item.size),
        date: displayDateFormatter.format(
          new Date(item.time * 1000),
          get(dateDisplayFormat)
        )
      };
    }

    return {
      size: 0,
      date: 0
    };
  };

  show(
    {
      title: t('database_backups.confirm.title'),
      message: t('database_backups.confirm.message', { ...messageInfo })
    },
    () => remove(item)
  );
};
</script>

<template>
  <Fragment>
    <DataTable
      :value="selected"
      :items="itemsWithIndex"
      sort-by="time"
      show-select
      item-key="index"
      :single-select="false"
      :headers="tableHeaders"
      :loading="loading"
      @input="onSelectedChange($event)"
    >
      <template #item.time="{ item }">
        <DateDisplay :timestamp="item.time" />
      </template>
      <template #item.size="{ item }">
        {{ size(item.size) }}
      </template>
      <template #item.actions="{ item }">
        <VTooltip top>
          <template #activator="{ on, attrs }">
            <VBtn
              v-bind="attrs"
              icon
              class="mx-1"
              v-on="on"
              @click="showDeleteConfirmation(item)"
            >
              <VIcon small> mdi-delete-outline </VIcon>
            </VBtn>
          </template>
          <span>{{ t('database_backups.action.delete') }}</span>
        </VTooltip>
        <VTooltip top>
          <template #activator="{ on, attrs }">
            <VBtn
              icon
              :href="getLink(item)"
              v-bind="attrs"
              class="mx-1"
              download
              v-on="on"
            >
              <VIcon small> mdi-download </VIcon>
            </VBtn>
          </template>
          <span>{{ t('database_backups.action.download') }}</span>
        </VTooltip>
      </template>
      <template #body.append="{ isMobile }">
        <RowAppend
          label-colspan="3"
          :label="t('common.total')"
          :right-patch-colspan="1"
          :is-mobile="isMobile"
        >
          {{ totalSize }}
        </RowAppend>
      </template>
    </DataTable>
  </Fragment>
</template>
