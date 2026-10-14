<script setup lang="ts">
import type { HistoryEventsRestrictions } from '@/modules/history/events/history-events-restrictions';
import type { StakingLocation } from '@/pages/staking/staking-pages';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import { provideHistoryEventsSection } from '@/modules/history/events/use-history-events-section';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import StakingLocationTitle from '@/modules/staking/components/StakingLocationTitle.vue';
import StakingRefreshActions from '@/modules/staking/components/StakingRefreshActions.vue';
import { useStakingHistorySync } from '@/modules/staking/use-staking-history-sync';

const { asset, chain, failedAddresses, loading, location, refresh, restrictions } = defineProps<{
  asset: string;
  /** The chain the staking events come from, which the refresh menu's history sync queries. */
  chain: string;
  /** The addresses whose staking positions could not be loaded. Nothing is shown while empty. */
  failedAddresses: string[];
  loading: boolean;
  /** The location the page shows, named in the breadcrumb and switchable from it. */
  location: StakingLocation;
  refresh: () => Promise<void>;
  restrictions: HistoryEventsRestrictions;
}>();

defineSlots<{
  default: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const { fetchPrices } = usePriceTaskManager();
const { getAddressName } = useAddressNameResolution();

// The page's Refresh covers the staking events too, so the events section drops its own.
const { reload: reloadEvents } = provideHistoryEventsSection();
const { chainName, syncHistory, syncingHistory } = useStakingHistorySync(reloadEvents, chain);

/** The failed addresses as the tables name them: by their address book name where there is one. */
const failedNames = computed<string>(() =>
  failedAddresses.map(address => getAddressName(address, chain) ?? address).join(', '));

async function load(ignoreCache: boolean = false): Promise<void> {
  await Promise.all([
    refresh(),
    fetchPrices({ ignoreCache, selectedAssets: [asset] }),
  ]);
}

async function refreshPage(): Promise<void> {
  await load(true);
  reloadEvents();
}

onMounted(async () => {
  await load();
});
</script>

<template>
  <TablePageLayout child>
    <template #title>
      <StakingLocationTitle :location="location" />
    </template>
    <template #buttons>
      <StakingRefreshActions
        :refreshing="loading"
        :syncing-history="syncingHistory"
        :chain-name="chainName"
        :tooltip="t('staking_page.refresh_tooltip')"
        test-id-prefix="staking"
        @refresh="refreshPage()"
        @sync-history="syncHistory()"
      />
    </template>

    <div class="flex flex-col gap-4">
      <RuiAlert
        v-if="failedAddresses.length > 0"
        type="warning"
        data-testid="staking-failed-addresses"
      >
        {{ t('staking_page.failed_addresses', { addresses: failedNames }, failedAddresses.length) }}
      </RuiAlert>

      <slot />

      <HistoryEventsView
        :section-title="t('common.events')"
        :restrictions="restrictions"
      />
    </div>
  </TablePageLayout>
</template>
