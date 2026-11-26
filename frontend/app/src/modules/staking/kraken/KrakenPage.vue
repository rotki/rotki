<script setup lang="ts">
import { RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { type RouteLocationRaw, useRouter } from 'vue-router';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import { provideHistoryEventsSection } from '@/modules/history/events/use-history-events-section';
import { usePremium } from '@/modules/premium/use-premium';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import StakingLocationTitle from '@/modules/staking/components/StakingLocationTitle.vue';
import KrakenStaking from '@/modules/staking/kraken/KrakenStaking.vue';
import KrakenStakingPagePlaceholder from '@/modules/staking/kraken/KrakenStakingPagePlaceholder.vue';
import { useKrakenStakingRefresh } from '@/modules/staking/kraken/use-kraken-staking-refresh';
import { useKrakenStakingStore } from '@/modules/staking/use-kraken-staking-store';

const store = useKrakenStakingStore();
const { dateFilter: filters, fetchError } = storeToRefs(store);
const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const premium = usePremium();

const isKrakenConnected = computed<boolean>(() => {
  const exchanges = get(connectedExchanges);
  return exchanges.some(({ location }) => location === 'kraken');
});

// The page's Refresh queries the Kraken staking events, so the events section drops its own.
const { reload: reloadEvents } = provideHistoryEventsSection();

const { refresh, refreshPage } = useKrakenStakingRefresh({
  connected: isKrakenConnected,
  reloadEvents,
});

/** The exchange keys form, opened on Kraken. */
const connectKrakenLink: RouteLocationRaw = {
  name: '/accounts/exchanges/',
  query: {
    add: 'true',
    location: 'kraken',
  },
};

const { isInitialLoading: loading, loading: refreshing } = storeToRefs(useKrakenStakingStore());

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
        :failure="fetchError"
        data-testid="kraken-staking-fetch-error"
        @retry="refresh()"
      />
      <KrakenStaking v-model="filters" />
    </template>
  </TablePageLayout>
</template>
