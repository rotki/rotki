<script setup lang="ts">
import { useAppRoutes } from '@/router/routes';
import type { ComputedRef } from 'vue';
import type { TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [
    Routes.ASSET_MANAGER_CEX_MAPPING,
    Routes.ASSET_MANAGER_NEWLY_DETECTED,
  ];
});

const { t } = useI18n();
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.manage_assets'),
      t('navigation_menu.manage_assets_sub.more'),
    ]"
  >
    <div class="flex justify-between">
      <TabNavigation
        :tabs="tabs"
        class="asset-manager-more"
        hide-router-view
        child
      />
    </div>
    <RouterView />
  </TablePageLayout>
</template>
