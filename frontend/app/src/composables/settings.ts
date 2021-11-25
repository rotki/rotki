import { computed } from '@vue/composition-api';
import { useStore } from '@/store/utils';
import { DashboardTablesShowedColumns } from '@/types/frontend-settings';

export const setupSettings = () => {
  const store = useStore();

  const dashboardTablesShowedColumns = computed<DashboardTablesShowedColumns>(
    () => store.getters['settings/dashboardTablesShowedColumns']
  );

  return {
    dashboardTablesShowedColumns
  };
};
