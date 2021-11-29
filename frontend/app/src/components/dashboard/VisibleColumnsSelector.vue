<template>
  <v-list>
    <v-list-item-group
      :value="currentVisibleColumns"
      multiple
      @change="onVisibleColumnsChange"
    >
      <template v-for="(item, i) in availableColumns">
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
import {
  computed,
  defineComponent,
  PropType,
  Ref,
  toRefs
} from '@vue/composition-api';
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import {
  DashboardTableType,
  DASHBOARD_TABLES_VISIBLE_COLUMNS,
  FrontendSettingsPayload
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';

const availableColumns = (groupLabel: Ref<string>, group: Ref<string>) =>
  computed(() => {
    return [
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
              group: groupLabel.value || group.value
            }
          )
          .toString()
      }
    ];
  });

export default defineComponent({
  name: 'VisibleColumnsSelector',
  props: {
    group: { required: true, type: String as PropType<DashboardTableType> },
    groupLabel: { required: false, type: String, default: '' }
  },
  setup(props) {
    const { group, groupLabel } = toRefs(props);

    const { dashboardTablesVisibleColumns, updateSetting } = setupSettings();

    const currentVisibleColumns = computed(() => {
      return dashboardTablesVisibleColumns.value[group.value];
    });

    const onVisibleColumnsChange = async (visibleColumns: TableColumn[]) => {
      const payload: FrontendSettingsPayload = {
        [DASHBOARD_TABLES_VISIBLE_COLUMNS]: {
          ...dashboardTablesVisibleColumns.value,
          [group.value]: visibleColumns
        }
      };

      await updateSetting(payload);
    };

    return {
      availableColumns: availableColumns(groupLabel, group),
      currentVisibleColumns,
      dashboardTablesVisibleColumns,
      onVisibleColumnsChange
    };
  }
});
</script>
