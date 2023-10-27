<script setup lang="ts">
import {
  type DashboardTableType,
  type FrontendSettingsPayload
} from '@/types/settings/frontend-settings';
import { TableColumn } from '@/types/table-column';

const props = withDefaults(
  defineProps<{
    group: DashboardTableType;
    groupLabel?: string;
  }>(),
  { groupLabel: undefined }
);

const { t } = useI18n();

const { group, groupLabel } = toRefs(props);

const availableColumns = computed(() => [
  {
    value: TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE,
    text: t(
      'dashboard_asset_table.headers.percentage_of_total_net_value'
    ).toString()
  },
  {
    value: TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP,
    text: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
      group: get(groupLabel) || get(group)
    }).toString()
  }
]);

const store = useFrontendSettingsStore();
const { dashboardTablesVisibleColumns } = storeToRefs(store);

const currentVisibleColumns = computed(
  () => get(dashboardTablesVisibleColumns)[get(group)]
);

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

<template>
  <VList>
    <VListItemGroup
      :value="currentVisibleColumns"
      multiple
      @change="onVisibleColumnsChange($event)"
    >
      <template v-for="(item, i) in availableColumns">
        <VListItem :key="i" :value="item.value">
          <template #default="{ active }">
            <VListItemContent>
              <VListItemTitle>
                {{ item.text }}
              </VListItemTitle>
            </VListItemContent>

            <VListItemAction>
              <VCheckbox :input-value="active" />
            </VListItemAction>
          </template>
        </VListItem>
      </template>
    </VListItemGroup>
  </VList>
</template>
