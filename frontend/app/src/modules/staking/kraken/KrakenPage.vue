<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import { provideHistoryEventsSection } from '@/modules/history/events/use-history-events-section';
import { usePremium } from '@/modules/premium/use-premium';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import StakingLocationTitle from '@/modules/staking/components/StakingLocationTitle.vue';
import KrakenStaking from '@/modules/staking/kraken/KrakenStaking.vue';
import KrakenStakingPagePlaceholder from '@/modules/staking/kraken/KrakenStakingPagePlaceholder.vue';
import { useKrakenStakingOperations } from '@/modules/staking/kraken/use-kraken-staking-operations';
import { useKrakenStakingStore } from '@/modules/staking/use-kraken-staking-store';

const store = useKrakenStakingStore();
const { dateFilter: filters, dateFilterKey, events, fetchError } = storeToRefs(store);
const { fetchEvents: load } = useKrakenStakingOperations();
const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
const { resetProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();

const { refreshPrices } = usePriceRefresh();
const failureMessage = useFailureMessage();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const premium = usePremium();

// The page's Refresh queries the Kraken staking events, so the events section drops its own.
const { reload: reloadEvents } = provideHistoryEventsSection();

/** The exchange keys form, opened on Kraken. */
const connectKrakenLink: RouteLocationRaw = {
  name: '/api-keys/exchanges/',
  query: {
    add: 'true',
    location: 'kraken',
  },
};

const { isInitialLoading: loading, loading: refreshing } = storeToRefs(useKrakenStakingStore());

const isKrakenConnected = computed<boolean>(() => {
  const exchanges = get(connectedExchanges);
  return exchanges.some(({ location }) => location === 'kraken');
});

async function refresh(ignoreCache: boolean = false): Promise<void> {
  resetProtocolStatsPriceQueryStatus('kraken');
  await load(ignoreCache);
  const assets = get(events).received.map(item => item.asset);
  await refreshPrices(ignoreCache, assets);
}

async function refreshPage(): Promise<void> {
  await refresh(true);
  reloadEvents();
}

/**
 * The date pills write a value per picker emit, and a year typed digit by digit emits once per
 * digit (`2` and `20` and `202` are each a valid date). Every write here is a POST to
 * `/staking/kraken` plus a price refresh, so the trigger is debounced and a burst of intermediate
 * dates settles into one query. The key is watched rather than the bounds themselves: it changes
 * only when a bound does, where the object it comes from is rewritten by any pagination change.
 * The debounced ref starts at the current value, so the first run after mount is not delayed.
 */
const settledDateFilterKey = refDebounced(dateFilterKey, 400);

watchImmediate([settledDateFilterKey, isKrakenConnected], async ([_, isKrakenConnected]) => {
  if (isKrakenConnected) {
    await refresh();
  }
});

onUnmounted(() => {
  store.$reset();
});
</script>

<template>
  <TablePageLayout child>
    <template #title>
      <StakingLocationTitle location="kraken" />
    </template>
    <template #buttons>
      <RuiTooltip
        v-if="premium && isKrakenConnected"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            data-testid="kraken-staking-refresh"
            :loading="refreshing || loading"
            @click="refreshPage()"
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
    <div
      v-else-if="!isKrakenConnected"
      class="rounded-rui-card border border-rui-divider bg-rui-surface"
      data-testid="kraken-staking-connect"
    >
      <TableEmptyNotice
        icon="lu-key-round"
        :title="t('kraken_page.connect.title')"
        :description="t('kraken_page.connect.description')"
      >
        <RuiButton
          color="primary"
          data-testid="kraken-staking-connect-button"
          @click="router.push(connectKrakenLink)"
        >
          <template #prepend>
            <RuiIcon name="lu-plus" />
          </template>
          {{ t('kraken_page.connect.action') }}
        </RuiButton>
      </TableEmptyNotice>
    </div>
    <ProgressScreen v-else-if="loading">
      <template #message>
        {{ t('kraken_page.loading') }}
      </template>
    </ProgressScreen>
    <template v-else>
      <FailureStrip
        v-if="fetchError"
        class="mb-4"
        :title="t('kraken_page.fetch_failed')"
        :message="failureMessage(fetchError)"
        data-testid="kraken-staking-fetch-error"
        @retry="refresh()"
      />
      <KrakenStaking v-model="filters" />
    </template>
  </TablePageLayout>
</template>
