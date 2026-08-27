<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { msg } from '@/message-key';
import OracleCacheContent from '@/modules/assets/prices/components/oracle/OracleCacheContent.vue';
import OraclePriceContent from '@/modules/assets/prices/components/oracle/OraclePriceContent.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_prices_sub.oracle_prices'), icon: 'lu-database', parent: '/price-manager/', order: 30, drawer: 'price-manager-oracle' },
  },
});

const { t } = useI18n({ useScope: 'global' });

const tab = ref<'prices' | 'caches'>('prices');

const oracleSettingsRoute: RouteLocationRaw = { name: '/settings/oracle/' };
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.manage_prices'), t('navigation_menu.manage_prices_sub.oracle_prices')]"
  >
    <template #buttons>
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RouterLink :to="oracleSettingsRoute">
            <RuiButton
              variant="text"
              icon
              color="primary"
              size="lg"
              data-testid="oracle-settings-link"
            >
              <RuiIcon name="lu-settings" />
            </RuiButton>
          </RouterLink>
        </template>
        <span>{{ t('oracle_prices.settings_tooltip') }}</span>
      </RuiTooltip>
    </template>

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
