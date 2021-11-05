<template>
  <data-table :items="items" sort-by="time" :headers="headers">
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
            @click="remove(item)"
          >
            <v-icon small> mdi-delete-outline </v-icon>
          </v-btn>
        </template>
        <span>{{ $t('database_backups.action.delete') }}</span>
      </v-tooltip>
    </template>
  </data-table>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import i18n from '@/i18n';
import { UserDbBackup } from '@/services/backup/types';

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
  props: {
    items: { required: true, type: Array as PropType<UserDbBackup[]> }
  },
  setup() {
    const size = (bytes: number) => {
      let i = 0;

      for (i; bytes > 1024; i++) {
        bytes /= 1024;
      }

      const symbol = 'KMGTPEZY'[i - 1] || '';
      return `${bytes.toFixed(2)}  ${symbol}B`;
    };
    const remove = (_backup: UserDbBackup) => {};
    return {
      remove,
      size,
      headers: tableHeaders
    };
  }
});
</script>
