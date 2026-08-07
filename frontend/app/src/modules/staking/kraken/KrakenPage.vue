<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { KrakenStakingDateFilter } from '@/modules/staking/staking-types';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import { usePremium } from '@/modules/premium/use-premium';
import AppImage from '@/modules/shell/components/AppImage.vue';
import FullSizeContent from '@/modules/shell/components/FullSizeContent.vue';
import InternalLink from '@/modules/shell/components/InternalLink.vue';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import KrakenStaking from '@/modules/staking/kraken/KrakenStaking.vue';
import KrakenStakingPagePlaceholder from '@/modules/staking/kraken/KrakenStakingPagePlaceholder.vue';
import { useKrakenStakingOperations } from '@/modules/staking/kraken/use-kraken-staking-operations';
import { useKrakenStakingStore } from '@/modules/staking/use-kraken-staking-store';

const filters = ref<KrakenStakingDateFilter>({});

const store = useKrakenStakingStore();
const { events } = toRefs(store);
const { fetchEvents: load } = useKrakenStakingOperations();
const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
const { resetProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();

const { refreshPrices } = usePriceRefresh();

const { t } = useI18n({ useScope: 'global' });

const premium = usePremium();

const addKrakenApiKeysLink: RouteLocationRaw = {
  name: '/api-keys/exchanges/',
  query: {
    add: 'true',
  },
};

const { isInitialLoading: loading, loading: refreshing } = storeToRefs(useKrakenStakingStore());

const isKrakenConnected = computed<boolean>(() => {
  const exchanges = get(connectedExchanges);
  return exchanges.some(({ location }) => location === 'kraken');
});

async function refresh(ignoreCache: boolean = false): Promise<void> {
  resetProtocolStatsPriceQueryStatus('kraken');
  await load(ignoreCache, get(filters));
  const assets = get(events).received.map(item => item.asset);
  await refreshPrices(ignoreCache, assets);
}

/**
 * The date pills write a value per picker emit, and a year typed digit by digit emits once per
 * digit (`2` and `20` and `202` are each a valid date). Every write here is a POST to
 * `/staking/kraken` plus a price refresh, so the trigger is debounced and a burst of intermediate
 * dates settles into one query. `refresh` reads the live `filters`, so it still queries the value
 * the user stopped on, and the debounced ref starts at the current value, so the first run after
 * mount is not delayed.
 */
const settledFilters = refDebounced(filters, 400);

watchImmediate([settledFilters, isKrakenConnected], async ([_, isKrakenConnected]) => {
  if (isKrakenConnected) {
    await refresh();
  }
});

onUnmounted(() => {
  store.$reset();
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking.kraken')]"
    child
  >
    <template #buttons>
      <RuiTooltip
        v-if="premium && isKrakenConnected"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="refreshing || loading"
            @click="refresh(true)"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('kraken_staking_events.refresh_tooltip') }}
      </RuiTooltip>
    </template>

    <KrakenStakingPagePlaceholder v-if="!premium" />
    <FullSizeContent
      v-else-if="!isKrakenConnected"
      class="gap-4"
    >
      <span class="font-bold text-h5">
        {{ t('kraken_page.page.title') }}
      </span>

      <InternalLink :to="addKrakenApiKeysLink">
        <AppImage
          width="64px"
          contain
          :src="getPublicProtocolImagePath('kraken.svg')"
        />
      </InternalLink>

      <i18n-t
        scope="global"
        tag="h6"
        keypath="kraken_page.page.description"
        class="font-light text-h6 text-rui-text-secondary"
      >
        <template #link>
          <InternalLink :to="addKrakenApiKeysLink">
            {{ t('kraken_page.page.api_key') }}
          </InternalLink>
        </template>
      </i18n-t>
    </FullSizeContent>
    <ProgressScreen v-else-if="loading">
      <template #message>
        {{ t('kraken_page.loading') }}
      </template>
    </ProgressScreen>
    <KrakenStaking
      v-else
      v-model="filters"
      :loading="refreshing"
    />
  </TablePageLayout>
</template>
