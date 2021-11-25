<template>
  <v-list>
    <v-list-item-group
      :value="showedColumns"
      multiple
      @change="onShowedColumnsChange"
    >
      <template v-for="(item, i) in columns">
        <v-list-item :key="i" :value="item.value">
          <template #default="{ active }">
            <v-list-item-content>
              <v-list-item-title v-text="item.text" />
            </v-list-item-content>

            <v-list-item-action>
              <v-checkbox :input-value="active" />
            </v-list-item-action>
          </template>
        </v-list-item>
      </template>
    </v-list-item-group>
  </v-list>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { mapGetters } from 'vuex';
import { BaseMessage } from '@/components/settings/utils';
import i18n from '@/i18n';
import SettingsMixin from '@/mixins/settings-mixin';
import {
  DashboardTableType,
  DASHBOARD_TABLES_SHOWED_COLUMNS,
  FrontendSettingsPayload
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';

export default defineComponent({
  name: 'ShowedColumnsSelector',
  mixins: [SettingsMixin],
  props: {
    group: { required: true, type: String as PropType<DashboardTableType> },
    groupLabel: { required: false, type: String, default: '' }
  },
  data() {
    return {
      columns: [
        {
          value: TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE,
          text: i18n
            .t('dashboard_asset_table.headers.percentage_of_total_net_value')
            .toString()
        },
        {
          value: TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP,
          text: i18n
            .t(
              'dashboard_asset_table.headers.percentage_of_total_current_group',
              {
                group: this.groupLabel || this.group
              }
            )
            .toString()
        }
      ]
    };
  },

  computed: {
    ...mapGetters('settings', ['dashboardTablesShowedColumns']),
    showedColumns(): TableColumn[] {
      return this.dashboardTablesShowedColumns[this.group];
    }
  },

  methods: {
    async onShowedColumnsChange(showedColumns: TableColumn[]) {
      const mixin = this as any as SettingsMixin<any>;

      const payload: FrontendSettingsPayload = {
        [DASHBOARD_TABLES_SHOWED_COLUMNS]: {
          ...this.dashboardTablesShowedColumns,
          [this.group]: showedColumns
        }
      };

      const messages: BaseMessage = {
        success: '',
        error: ''
      };

      await mixin.modifyFrontendSetting(
        payload,
        'dashboardTablesShowedColumns',
        messages
      );
    }
  }
});
</script>
