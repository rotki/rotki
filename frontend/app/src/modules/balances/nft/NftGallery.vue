<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import NftGalleryActions from '@/modules/balances/nft/NftGalleryActions.vue';
import NftGalleryEmptyState from '@/modules/balances/nft/NftGalleryEmptyState.vue';
import NftGalleryFilters from '@/modules/balances/nft/NftGalleryFilters.vue';
import NftGalleryGrid from '@/modules/balances/nft/NftGalleryGrid.vue';
import NftGalleryPremiumAlert from '@/modules/balances/nft/NftGalleryPremiumAlert.vue';
import { useNftGalleryData } from '@/modules/balances/nft/use-nft-gallery-data';
import { useNftGalleryFilters } from '@/modules/balances/nft/use-nft-gallery-filters';
import { useNftGalleryLayout } from '@/modules/balances/nft/use-nft-gallery-layout';
import { usePremium } from '@/modules/premium/use-premium';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import InternalLink from '@/modules/shell/components/InternalLink.vue';
import NoDataScreen from '@/modules/shell/components/NoDataScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();
const { useApiKey } = useExternalApiKeys();

const {
  error,
  fetchNfts,
  fetchPrices,
  limit,
  loading,
  nftLimited,
  nfts,
  perAccount,
  total,
} = useNftGalleryData();

const {
  availableAddresses,
  collections,
  items,
  modelSelectedAccounts,
  modelSelectedCollection,
  modelSortBy,
  modelSortDescending,
} = useNftGalleryFilters(nfts, perAccount);

const { firstLimit, paginationData, visibleNfts } = useNftGalleryLayout(items);

const noData = computed<boolean>(() =>
  get(visibleNfts).length === 0 && !(get(modelSelectedCollection) || get(modelSelectedAccounts).length > 0),
);

const openSeaKey = useApiKey('opensea');
const hasOpenSeaKey = computed<boolean>(() => !!get(openSeaKey));

const apiKeysRoute: RouteLocationRaw = { name: '/api-keys/external/', query: { service: 'opensea' } };

watch([firstLimit, modelSelectedAccounts, modelSelectedCollection], () => {
  set(paginationData, { ...get(paginationData), page: 1 });
});

/**
 * Fetches once there is a key, not only on mount: right after login the keys are still loading
 * when the page mounts, and a mount-only check left the page on its loading screen for good.
 */
watchImmediate(hasOpenSeaKey, (hasKey, hadKey) => {
  if (!hasKey || hadKey)
    return;

  fetchPrices();
  fetchNfts();
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.nfts')]">
    <template
      v-if="hasOpenSeaKey"
      #buttons
    >
      <NftGalleryActions
        :loading="loading"
        @refresh="fetchNfts(true)"
      />
    </template>

    <NoDataScreen
      v-if="!hasOpenSeaKey"
      icon="lu-key-round"
      data-testid="nft-gallery-key-required"
    >
      <template #title>
        {{ t('nft_gallery.api_key_required_title') }}
      </template>
      <i18n-t
        scope="global"
        keypath="nft_gallery.api_key_required_message"
      >
        <template #link>
          <InternalLink :to="apiKeysRoute">
            {{ t('nft_gallery.opensea_settings_link') }}
          </InternalLink>
        </template>
      </i18n-t>
    </NoDataScreen>
    <div
      v-else-if="loading && visibleNfts.length === 0"
      class="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 gap-4"
      role="status"
      :aria-label="t('nft_gallery.loading')"
      data-testid="nft-gallery-skeleton"
    >
      <RuiCard
        v-for="index in 8"
        :key="index"
        no-padding
        class="overflow-hidden"
      >
        <div class="aspect-square">
          <RuiSkeletonLoader class="size-full rounded-none" />
        </div>
        <div class="p-4 flex flex-col gap-2">
          <RuiSkeletonLoader class="h-5 w-3/4" />
          <RuiSkeletonLoader class="h-4 w-1/2" />
          <RuiSkeletonLoader class="h-4 w-1/3 mt-3" />
        </div>
      </RuiCard>
    </div>
    <NftGalleryEmptyState
      v-else-if="noData"
      :error="error"
      :nft-limited="nftLimited"
    />
    <div
      v-else
      class="flex flex-col gap-6"
    >
      <NftGalleryFilters
        v-model:selected-accounts="modelSelectedAccounts"
        v-model:selected-collection="modelSelectedCollection"
        v-model:sort-by="modelSortBy"
        v-model:sort-descending="modelSortDescending"
        :available-addresses="availableAddresses"
        :collections="collections"
      />

      <NftGalleryPremiumAlert
        :limit="limit"
        :premium="premium"
        :total="total"
      />

      <NftGalleryGrid :items="visibleNfts" />
      <div class="rounded-rui-card border border-rui-divider bg-rui-surface">
        <RuiTablePagination v-model="paginationData" />
      </div>
    </div>
  </TablePageLayout>
</template>
