<script setup lang="ts">
import type { Module } from '@/types/modules';
import NoDataScreen from '@/components/common/NoDataScreen.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import NftGalleryActions from '@/components/nft/NftGalleryActions.vue';
import NftGalleryEmptyState from '@/components/nft/NftGalleryEmptyState.vue';
import NftGalleryFilters from '@/components/nft/NftGalleryFilters.vue';
import NftGalleryGrid from '@/components/nft/NftGalleryGrid.vue';
import NftGalleryPremiumAlert from '@/components/nft/NftGalleryPremiumAlert.vue';
import { useNftGalleryData } from '@/composables/nft/use-nft-gallery-data';
import { useNftGalleryFilters } from '@/composables/nft/use-nft-gallery-filters';
import { useNftGalleryLayout } from '@/composables/nft/use-nft-gallery-layout';
import { usePremium } from '@/composables/premium';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';

const { modules } = defineProps<{ modules: Module[] }>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const premium = usePremium();
const { apiKey } = useExternalApiKeys(t);

// Use composables
const {
  error,
  fetchNfts,
  fetchPrices,
  limit,
  loading,
  nftLimited,
  nfts,
  perAccount,
} = useNftGalleryData();

const {
  availableAddresses,
  collections,
  items,
  selectedAccounts,
  selectedCollection,
  sortBy,
  sortDescending,
} = useNftGalleryFilters(nfts, perAccount);

const { firstLimit, paginationData, visibleNfts } = useNftGalleryLayout(items);

// Computed properties
const noData = computed<boolean>(() =>
  get(visibleNfts).length === 0 && !(get(selectedCollection) || get(selectedAccounts).length > 0),
);

const openSeaKey = apiKey('opensea');
const hasOpenSeaKey = computed<boolean>(() => !!get(openSeaKey));

// Methods
function navigateToApiKeys(): void {
  router.push('/api-keys/external?service=opensea');
}

// Watchers
watch([firstLimit, selectedAccounts, selectedCollection], () => {
  set(paginationData, { ...get(paginationData), page: 1 });
});

// Lifecycle
onMounted(() => {
  if (get(hasOpenSeaKey)) {
    fetchPrices();
    fetchNfts();
  }
});
</script>

<template>
  <div v-if="!hasOpenSeaKey">
    <NoDataScreen full>
      <template #title>
        {{ t('nft_gallery.api_key_required_title') }}
      </template>
      <div>
        <i18n-t
          scope="global"
          keypath="nft_gallery.api_key_required_message"
        >
          <template #link>
            <RuiButton
              color="primary"
              variant="text"
              class="inline -my-2 [&>span]:underline"
              @click="navigateToApiKeys()"
            >
              {{ t('nft_gallery.opensea_settings_link') }}
            </RuiButton>
          </template>
        </i18n-t>
      </div>
    </NoDataScreen>
  </div>
  <ProgressScreen v-else-if="loading && visibleNfts.length === 0">
    {{ t('nft_gallery.loading') }}
  </ProgressScreen>
  <NftGalleryEmptyState
    v-else-if="noData"
    :error="error"
    :nft-limited="nftLimited"
    @refresh="fetchNfts()"
  />
  <TablePageLayout
    v-else
    class="p-4"
    :title="[t('navigation_menu.nfts')]"
  >
    <template #buttons>
      <NftGalleryActions
        :modules="modules"
        :loading="loading"
        @refresh="fetchNfts(true)"
      />
    </template>

    <div class="flex flex-col gap-6">
      <NftGalleryFilters
        v-model:selected-accounts="selectedAccounts"
        v-model:selected-collection="selectedCollection"
        v-model:sort-by="sortBy"
        v-model:sort-descending="sortDescending"
        :available-addresses="availableAddresses"
        :collections="collections"
      />

      <NftGalleryPremiumAlert
        :limit="limit"
        :premium="premium"
        :visible-count="visibleNfts.length"
      />

      <NftGalleryGrid :items="visibleNfts" />
    </div>
    <RuiCard>
      <RuiTablePagination v-model="paginationData" />
    </RuiCard>
  </TablePageLayout>
</template>
