<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { msg } from '@/message-key';
import OracleCacheContent from '@/modules/assets/prices/components/oracle/OracleCacheContent.vue';
import OraclePriceContent from '@/modules/assets/prices/components/oracle/OraclePriceContent.vue';
import OracleTabs from '@/modules/assets/prices/components/oracle/OracleTabs.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_prices_sub.oracle_prices'), icon: 'lu-database', parent: '/price-manager/', order: 30, drawer: 'price-manager-oracle' },
  },
  // the router only matches the two tabs; without one, the page shows prices
  path: '/price-manager/oracle/:tab(prices|caches)?',
  props: true,
});

const { tab: routeTab } = defineProps<{
  tab?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

/** The shown tab lives in the route, so a reload or a shared link opens the same one. */
const tab = computed<'prices' | 'caches'>({
  get: () => (routeTab === 'caches' ? 'caches' : 'prices'),
  set: (value) => {
    if (value !== get(tab))
      router.push(`/price-manager/oracle/${value}`);
  },
});

const addCacheOpen = ref<boolean>(false);

const prices = useTemplateRef<InstanceType<typeof OraclePriceContent>>('prices');
const caches = useTemplateRef<InstanceType<typeof OracleCacheContent>>('caches');

const oracleSettingsRoute: RouteLocationRaw = { name: '/settings/oracle/' };

/** The header's refresh acts on the shown tab. */
const refreshing = computed<boolean>(() => (get(tab) === 'prices' ? get(prices)?.loading : get(caches)?.loadingCaches) ?? false);

const refreshTooltip = computed<string>(() => (get(tab) === 'prices'
  ? t('oracle_prices.refresh_tooltip')
  : t('oracle_prices.cache.refresh_tooltip')));

async function refresh(): Promise<void> {
  if (get(tab) === 'prices')
    await get(prices)?.refresh();
  else
    await get(caches)?.loadCaches();
}
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.manage_prices'), t('navigation_menu.manage_prices_sub.oracle_prices')]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="refreshing"
            data-testid="oracle-refresh"
            @click="refresh()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ refreshTooltip }}
      </RuiTooltip>
      <RuiButton
        v-if="tab === 'caches'"
        color="primary"
        data-testid="oracle-cache-add"
        @click="addCacheOpen = true"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('oracle_prices.cache.add') }}
      </RuiButton>
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RouterLink :to="oracleSettingsRoute">
            <RuiButton
              variant="text"
              icon
              class="text-rui-text-secondary!"
              :aria-label="t('oracle_prices.settings_tooltip')"
              data-testid="oracle-settings-link"
            >
              <RuiIcon name="lu-settings" />
            </RuiButton>
          </RouterLink>
        </template>
        <span>{{ t('oracle_prices.settings_tooltip') }}</span>
      </RuiTooltip>
    </template>

    <KeepAlive>
      <OraclePriceContent
        v-if="tab === 'prices'"
        ref="prices"
      >
        <template #tabs>
          <OracleTabs v-model="tab" />
        </template>
      </OraclePriceContent>
      <OracleCacheContent
        v-else
        ref="caches"
        v-model:add-open="addCacheOpen"
      >
        <template #tabs>
          <OracleTabs v-model="tab" />
        </template>
      </OracleCacheContent>
    </KeepAlive>
  </TablePageLayout>
</template>
