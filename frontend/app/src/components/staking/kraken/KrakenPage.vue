<script setup lang="ts">
import type { KrakenStakingDateFilter } from '@/types/staking';
import type { RouteLocationRaw } from 'vue-router';
import AppImage from '@/components/common/AppImage.vue';
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import InternalLink from '@/components/helper/InternalLink.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import KrakenStaking from '@/components/staking/kraken/KrakenStaking.vue';
import { useBalances } from '@/composables/balances';
import { Routes } from '@/router/routes';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useKrakenStakingStore } from '@/store/staking/kraken';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';

const filters = ref<KrakenStakingDateFilter>({});

const { isLoading, shouldShowLoadingScreen } = useStatusStore();
const store = useKrakenStakingStore();
const { $reset, load } = store;
const { events } = toRefs(store);
const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
const { resetProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();

const { refreshPrices } = useBalances();

const { t } = useI18n({ useScope: 'global' });

const addKrakenApiKeysLink: RouteLocationRaw = {
  path: `${Routes.API_KEYS_EXCHANGES}`,
  query: {
    add: 'true',
  },
};

const loading = shouldShowLoadingScreen(Section.STAKING_KRAKEN);
const refreshing = isLoading(Section.STAKING_KRAKEN);

const isKrakenConnected = computed(() => {
  const exchanges = get(connectedExchanges);
  return exchanges.some(({ location }) => location === 'kraken');
});

async function refresh(ignoreCache: boolean = false) {
  resetProtocolStatsPriceQueryStatus('kraken');
  await load(ignoreCache, get(filters));
  const assets = get(events).received.map(item => item.asset);
  await refreshPrices(ignoreCache, assets);
}

watchImmediate([filters, isKrakenConnected], async ([_, isKrakenConnected]) => {
  if (isKrakenConnected) {
    await refresh();
  }
});

onUnmounted(() => {
  $reset();
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking.kraken')]"
    child
  >
    <template #buttons>
      <RuiTooltip
        v-if="isKrakenConnected"
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

    <FullSizeContent
      v-if="!isKrakenConnected"
      class="gap-4"
    >
      <span class="font-bold text-h5">
        {{ t('kraken_page.page.title') }}
      </span>

      <InternalLink :to="addKrakenApiKeysLink">
        <AppImage
          width="64px"
          contain
          src="/assets/images/protocols/kraken.svg"
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
