import { computed } from '@vue/composition-api';
import { useStore } from '@/store/utils';
import {
  DashboardTablesVisibleColumns,
  FrontendSettingsPayload
} from '@/types/frontend-settings';

export const setupSettings = () => {
  const store = useStore();

  const dashboardTablesVisibleColumns = computed<DashboardTablesVisibleColumns>(
    () => store.getters['settings/dashboardTablesVisibleColumns']
  );

  const updateSetting = async (
    settings: FrontendSettingsPayload
  ): Promise<void> => {
    await store.dispatch('settings/updateSetting', settings);
  };

  return {
    dashboardTablesVisibleColumns,
    updateSetting
  };
};
