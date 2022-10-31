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
              <v-list-item-title>
                {{ item.text }}
              </v-list-item-title>
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
<script setup lang="ts">
import { PropType } from 'vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import {
  DashboardTableType,
  FrontendSettingsPayload
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';

const { t } = useI18n();

const props = defineProps({
  group: { required: true, type: String as PropType<DashboardTableType> },
  groupLabel: { required: false, type: String, default: '' }
});

const { group, groupLabel } = toRefs(props);

const availableColumns = computed(() => {
  return [
    {
      value: TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE,
      text: t(
        'dashboard_asset_table.headers.percentage_of_total_net_value'
      ).toString()
    },
    {
      value: TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP,
      text: t(
        'dashboard_asset_table.headers.percentage_of_total_current_group',
        {
          group: get(groupLabel) || get(group)
        }
      ).toString()
    }
  ];
});

const store = useFrontendSettingsStore();
const { dashboardTablesVisibleColumns } = storeToRefs(store);

const currentVisibleColumns = computed(() => {
  return get(dashboardTablesVisibleColumns)[get(group)];
});

const onVisibleColumnsChange = async (visibleColumns: TableColumn[]) => {
  const payload: FrontendSettingsPayload = {
    dashboardTablesVisibleColumns: {
      ...get(dashboardTablesVisibleColumns),
      [get(group)]: visibleColumns
    }
  };

  await store.updateSetting(payload);
};
</script>
