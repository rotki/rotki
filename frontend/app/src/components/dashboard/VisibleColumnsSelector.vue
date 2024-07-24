<script setup lang="ts">
import { TableColumn } from '@/types/table-column';
import type { DashboardTableType, FrontendSettingsPayload } from '@/types/settings/frontend-settings';

const props = withDefaults(
  defineProps<{
    group: DashboardTableType;
    groupLabel?: string;
  }>(),
  { groupLabel: undefined },
);

const { t } = useI18n();

const { group, groupLabel } = toRefs(props);

const availableColumns = computed(() => [
  {
    value: TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE,
    text: t('dashboard_asset_table.headers.percentage_of_total_net_value'),
  },
  {
    value: TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP,
    text: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
      group: get(groupLabel) || get(group),
    }),
  },
]);

const store = useFrontendSettingsStore();
const { dashboardTablesVisibleColumns } = storeToRefs(store);

const currentVisibleColumns = computed(() => get(dashboardTablesVisibleColumns)[get(group)]);

async function onVisibleColumnsChange(visibleColumns: TableColumn[]) {
  const payload: FrontendSettingsPayload = {
    dashboardTablesVisibleColumns: {
      ...get(dashboardTablesVisibleColumns),
      [get(group)]: visibleColumns,
    },
  };

  await store.updateSetting(payload);
}

function active(value: TableColumn) {
  return get(currentVisibleColumns).includes(value);
}

function update(value: TableColumn) {
  const visible = [...get(currentVisibleColumns)];
  const index = visible.indexOf(value);
  if (index === -1)
    visible.push(value);
  else visible.splice(index, 1);

  onVisibleColumnsChange(visible);
}
</script>

<template>
  <div class="py-2">
    <template
      v-for="item in availableColumns"
      :key="item.value"
    >
      <RuiButton
        variant="list"
        size="sm"
        :model-value="item.value"
        @click="update(item.value)"
      >
        <template #prepend>
          <RuiCheckbox
            class="-mr-2"
            color="primary"
            hide-details
            :model-value="active(item.value)"
            @update:model-value="update(item.value)"
          />
        </template>
        {{ item.text }}
      </RuiButton>
    </template>
  </div>
</template>
