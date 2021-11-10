<template>
  <fragment>
    <data-table
      :items="items"
      sort-by="time"
      :headers="headers"
      :loading="loading"
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
              small
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
              small
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
        <tr>
          <td :colspan="isMobile ? 1 : 2" class="font-weight-medium">
            {{ $t('database_backups.row.total') }}
          </td>
          <td class="text-right">
            {{ totalSize }}
          </td>
          <td v-if="!isMobile" />
        </tr>
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
import { DataTableHeader } from 'vuetify';
import Fragment from '@/components/helper/Fragment';
import { getFilepath } from '@/components/settings/data-security/backups/utils';
import { dateDisplayFormat } from '@/composables/session';
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
  components: { Fragment },
  props: {
    items: { required: true, type: Array as PropType<UserDbBackup[]> },
    loading: { required: false, type: Boolean, default: false },
    directory: { required: true, type: String }
  },
  emits: ['remove'],
  setup(props, { emit }) {
    const { items, directory } = toRefs(props);
    const pendingDeletion = ref<UserDbBackup | null>(null);

    const messageInfo = computed(() => {
      const db = pendingDeletion.value;
      if (db) {
        return {
          size: size(db.size),
          date: displayDateFormatter.format(
            new Date(db.time * 1000),
            dateDisplayFormat.value
          )
        };
      }

      return {
        size: 0,
        date: 0
      };
    });

    const remove = () => {
      const value = pendingDeletion.value;
      pendingDeletion.value = null;
      emit('remove', value);
    };

    const totalSize = computed(() =>
      size(items.value.reduce((sum, db) => sum + db.size, 0))
    );

    const getLink = (db: UserDbBackup) =>
      api.backups.fileUrl(getFilepath(db, directory));

    return {
      remove,
      getLink,
      messageInfo,
      pendingDeletion,
      size,
      totalSize,
      headers: tableHeaders
    };
  }
});
</script>
