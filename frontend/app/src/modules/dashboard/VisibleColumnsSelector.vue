<script setup lang="ts">
import type { ButtonProps } from '@rotki/ui-library';
import type { DashboardTableType, FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import { TableColumn } from '@/modules/core/table/table-column';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';

const { group, groupLabel, size } = defineProps<{
  group: DashboardTableType;
  groupLabel?: string;
  /** Button size; without it the button keeps its 48px square. */
  size?: ButtonProps['size'];
}>();

const { t } = useI18n({ useScope: 'global' });

const availableColumns = computed(() => [
  {
    text: t('dashboard_asset_table.headers.percentage_of_total_net_value'),
    value: TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE,
  },
  {
    text: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
      group: groupLabel || group,
    }),
    value: TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP,
  },
]);

const dashboardTablesVisibleColumns = useSetting('dashboardTablesVisibleColumns');
const { updateFrontendSetting } = useSettingsOperations();

const currentVisibleColumns = computed(() => get(dashboardTablesVisibleColumns)[group]);

async function onVisibleColumnsChange(visibleColumns: TableColumn[]) {
  const payload: FrontendSettingsPayload = {
    dashboardTablesVisibleColumns: {
      ...get(dashboardTablesVisibleColumns),
      [group]: visibleColumns,
    },
  };

  await updateFrontendSetting(payload);
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
  <RuiMenu :options="{ placement: 'bottom-end' }">
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="t('dashboard_asset_table.select_visible_columns')"
        :size="size"
        v-bind="attrs"
      >
        <RuiIcon name="lu-ellipsis-vertical" />
      </MenuTooltipButton>
    </template>
    <!-- sized by its labels, which wrap past 20rem rather than run out of the menu -->
    <div class="w-max max-w-80 py-2">
      <div class="px-4 pb-1 text-caption uppercase tracking-wide text-rui-text-secondary">
        {{ t('dashboard_asset_table.visible_columns') }}
      </div>
      <div
        v-for="item in availableColumns"
        :key="item.value"
        class="px-4 py-1"
      >
        <RuiCheckbox
          color="primary"
          size="sm"
          hide-details
          :label="item.text"
          :model-value="active(item.value)"
          @update:model-value="update(item.value)"
        />
      </div>
    </div>
  </RuiMenu>
</template>
