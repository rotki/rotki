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

const active = (value: TableColumn) =>
  get(currentVisibleColumns).includes(value);

const update = (value: TableColumn) => {
  const visible = [...get(currentVisibleColumns)];
  const index = visible.indexOf(value);
  if (index === -1) {
    visible.push(value);
  } else {
    visible.splice(index, 1);
  }

  onVisibleColumnsChange(visible);
};
</script>

<template>
  <div class="py-2">
    <template v-for="item in availableColumns">
      <RuiButton
        :key="item.value"
        variant="list"
        class="py-1 [&>span:first-child]:flex-1"
        :value="item.value"
        @click="update(item.value)"
      >
        {{ item.text }}

        <template #append>
          <RuiCheckbox
            class="!p-0 pl-2"
            color="primary"
            hide-details
            :value="active(item.value)"
            @input="update(item.value)"
          />
        </template>
      </RuiButton>
    </template>
  </div>
</template>
