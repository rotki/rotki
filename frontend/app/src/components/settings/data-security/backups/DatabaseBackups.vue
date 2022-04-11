<template>
  <fragment>
    <data-table
      :value="selected"
      :items="items"
      sort-by="time"
      show-select
      item-key="time"
      :single-select="false"
      :headers="headers"
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
          <span>{{ $t('database_backups.action.delete') }}</span>
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
          <span>{{ $t('database_backups.action.download') }}</span>
        </v-tooltip>
      </template>
      <template #body.append="{ isMobile }">
        <row-append
          label-colspan="3"
          :label="$t('database_backups.row.total')"
          :right-patch-colspan="1"
          :is-mobile="isMobile"
        >
          {{ totalSize }}
        </row-append>
      </template>
    </data-table>
    <confirm-dialog
      :display="!!pendingDeletion"
      :title="$t('database_backups.confirm.title')"
      :message="$t('database_backups.confirm.message', messageInfo)"
      @cancel="pendingDeletion = null"
      @confirm="remove"
    />
  </fragment>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import Fragment from '@/components/helper/Fragment';
import RowAppend from '@/components/helper/RowAppend.vue';
import { getFilepath } from '@/components/settings/data-security/backups/utils';
import { setupGeneralSettings } from '@/composables/session';
import { displayDateFormatter } from '@/data/date_formatter';
import i18n from '@/i18n';
import { UserDbBackup } from '@/services/backup/types';
import { api } from '@/services/rotkehlchen-api';
import { size } from '@/utils/data';

const tableHeaders: DataTableHeader[] = [
  {
    value: 'version',
    text: i18n.t('database_backups.column.version').toString()
  },
  {
    value: 'time',
    text: i18n.t('database_backups.column.time').toString()
  },
  {
    value: 'size',
    align: 'end',
    text: i18n.t('database_backups.column.size').toString()
  },
  { value: 'actions', align: 'end', sortable: false, text: '' }
];

export default defineComponent({
  name: 'DatabaseBackups',
  components: {
    RowAppend,
    Fragment
  },
  props: {
    items: { required: true, type: Array as PropType<UserDbBackup[]> },
    selected: { required: true, type: Array as PropType<UserDbBackup[]> },
    loading: { required: false, type: Boolean, default: false },
    directory: { required: true, type: String }
  },
  emits: ['change', 'remove'],
  setup(props, { emit }) {
    const { items, directory } = toRefs(props);
    const pendingDeletion = ref<UserDbBackup | null>(null);

    const { dateDisplayFormat } = setupGeneralSettings();

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
      emit('remove', value);
    };

    const totalSize = computed(() =>
      size(get(items).reduce((sum, db) => sum + db.size, 0))
    );

    const getLink = (db: UserDbBackup) =>
      api.backups.fileUrl(getFilepath(db, directory));

    const onSelectedChange = (selected: UserDbBackup[]) => {
      emit('change', selected);
    };

    return {
      remove,
      getLink,
      onSelectedChange,
      messageInfo,
      pendingDeletion,
      size,
      totalSize,
      headers: tableHeaders
    };
  }
});
</script>
