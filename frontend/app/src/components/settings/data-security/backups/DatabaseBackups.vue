<template>
  <fragment>
    <data-table
      :value="selected"
      :items="itemsWithIndex"
      sort-by="time"
      show-select
      item-key="index"
      :single-select="false"
      :headers="tableHeaders"
      :loading="loading"
      @input="onSelectedChange"
    >
      <template #item.time="{ item }">
        <date-display :timestamp="item.time" />
      </template>
      <template #item.size="{ item }">
        {{ size(item.size) }}
      </template>
      <template #item.actions="{ item }">
        <v-tooltip top>
          <template #activator="{ on, attrs }">
            <v-btn
              v-bind="attrs"
              icon
              class="mx-1"
              v-on="on"
              @click="pendingDeletion = item"
            >
              <v-icon small> mdi-delete-outline </v-icon>
            </v-btn>
          </template>
          <span>{{ tc('database_backups.action.delete') }}</span>
        </v-tooltip>
        <v-tooltip top>
          <template #activator="{ on, attrs }">
            <v-btn
              icon
              :href="getLink(item)"
              v-bind="attrs"
              class="mx-1"
              download
              v-on="on"
            >
              <v-icon small> mdi-download </v-icon>
            </v-btn>
          </template>
          <span>{{ tc('database_backups.action.download') }}</span>
        </v-tooltip>
      </template>
      <template #body.append="{ isMobile }">
        <row-append
          label-colspan="3"
          :label="tc('common.total')"
          :right-patch-colspan="1"
          :is-mobile="isMobile"
        >
          {{ totalSize }}
        </row-append>
      </template>
    </data-table>
    <confirm-dialog
      :display="!!pendingDeletion"
      :title="tc('database_backups.confirm.title')"
      :message="tc('database_backups.confirm.message', 0, messageInfo)"
      @cancel="pendingDeletion = null"
      @confirm="remove"
    />
  </fragment>
</template>

<script setup lang="ts">
import { ComputedRef, PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import Fragment from '@/components/helper/Fragment';
import RowAppend from '@/components/helper/RowAppend.vue';
import { displayDateFormatter } from '@/data/date_formatter';
import { useBackupApi } from '@/services/backup';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { UserDbBackup } from '@/types/backup';
import { assert } from '@/utils/assertions';
import { getFilepath } from '@/utils/backups';
import { size } from '@/utils/data';

const props = defineProps({
  items: { required: true, type: Array as PropType<UserDbBackup[]> },
  selected: { required: true, type: Array as PropType<UserDbBackup[]> },
  loading: { required: false, type: Boolean, default: false },
  directory: { required: true, type: String }
});

const emit = defineEmits<{
  (e: 'change', backup: UserDbBackup[]): void;
  (e: 'remove', backup: UserDbBackup): void;
}>();

const { tc } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    value: 'version',
    text: tc('database_backups.column.version')
  },
  {
    value: 'time',
    text: tc('common.datetime')
  },
  {
    value: 'size',
    align: 'end',
    text: tc('database_backups.column.size')
  },
  { value: 'actions', align: 'end', sortable: false, text: '' }
]);

const { items, directory } = toRefs(props);
const pendingDeletion = ref<UserDbBackup | null>(null);

const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());

const messageInfo = computed(() => {
  const db = get(pendingDeletion);
  if (db) {
    return {
      size: size(db.size),
      date: displayDateFormatter.format(
        new Date(db.time * 1000),
        get(dateDisplayFormat)
      )
    };
  }

  return {
    size: 0,
    date: 0
  };
});

const remove = () => {
  const value = get(pendingDeletion);
  set(pendingDeletion, null);
  assert(value);
  emit('remove', value);
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
  computed(() => {
    return get(items).map((item, index) => ({
      ...item,
      index
    }));
  });
</script>
