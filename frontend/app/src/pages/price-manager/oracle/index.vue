<script setup lang="ts">
import OracleCacheContent from '@/modules/assets/prices/components/oracle/OracleCacheContent.vue';
import OraclePriceContent from '@/modules/assets/prices/components/oracle/OraclePriceContent.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  name: 'price-manager-oracle',
});

const { t } = useI18n({ useScope: 'global' });

const tab = ref<'prices' | 'caches'>('prices');
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.manage_prices'), t('navigation_menu.manage_prices_sub.oracle_prices')]"
  >
    <div>
      <RuiTabs
        v-model="tab"
        color="primary"
        class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-3"
      >
        <RuiTab value="prices">
          {{ t('oracle_prices.tabs.prices') }}
        </RuiTab>
        <RuiTab value="caches">
          {{ t('oracle_prices.tabs.caches') }}
        </RuiTab>
      </RuiTabs>
      <RuiTabItems v-model="tab">
        <RuiTabItem value="prices">
          <OraclePriceContent />
        </RuiTabItem>
        <RuiTabItem value="caches">
          <OracleCacheContent />
        </RuiTabItem>
      </RuiTabItems>
    </div>
  </TablePageLayout>
</template>
