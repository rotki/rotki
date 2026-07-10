<script setup lang="ts">
import TabNavigation from '@/modules/shell/components/TabNavigation.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useNavTabs } from '@/modules/shell/layout/use-nav-tabs';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.manage_assets_sub.more', icon: 'lu-more-assets', parent: '/asset-manager/', order: 30, drawer: 'asset-manager-more' },
  },
  redirect: '/asset-manager/more/cex-mapping',
});

const tabs = useNavTabs([
  '/asset-manager/more/cex-mapping/',
  '/asset-manager/more/counterparty-mapping/',
  '/asset-manager/more/newly-detected/',
  '/asset-manager/more/missing-mappings/',
  '/asset-manager/more/solana-token-migration/',
]);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.manage_assets'), t('navigation_menu.manage_assets_sub.more')]">
    <div class="flex justify-between flex-1">
      <TabNavigation
        :tabs="tabs"
        class="asset-manager-more max-w-full lg:max-w-[calc(100%-300px)]"
        hide-router-view
        child
      />
    </div>
    <RouterView class="-mt-5 lg:-mt-[4.5rem]" />
  </TablePageLayout>
</template>
