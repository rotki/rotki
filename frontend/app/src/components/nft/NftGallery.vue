<script setup lang="ts">
import { BigNumber, Blockchain } from '@rotki/common';
import { type TablePaginationData, useBreakpoint } from '@rotki/ui-library';
import { keyBy } from 'lodash-es';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { Module } from '@/types/modules';
import type { GalleryNft, Nft, Nfts } from '@/types/nfts';
import type { NftPrice } from '@/types/prices';

defineProps<{ modules: Module[] }>();

const { t } = useI18n();

const prices = ref<Record<string, NftPrice>>({});
const priceError = ref('');
const total = ref(0);
const limit = ref(0);
const error = ref('');
const loading = ref(true);
const perAccount = ref<Nfts | null>(null);
const sortBy = ref<'name' | 'priceUsd' | 'collection'>('name');
const sortDescending = ref(false);

const chains = [Blockchain.ETH];

const page = ref(1);
const itemsPerPage = ref(8);

const { isSmAndDown, isSm, isMd, is2xl } = useBreakpoint();

const firstLimit = computed(() => {
  if (get(isSmAndDown))
    return 1;

  if (get(isSm))
    return 2;

  if (get(isMd))
    return 6;

  if (get(is2xl))
    return 10;

  return 8;
});

const limits = computed(() => {
  const first = get(firstLimit);
  return [first, first * 2, first * 4];
});

watchImmediate(firstLimit, () => {
  set(itemsPerPage, get(firstLimit));
});

const selectedAccounts = ref<BlockchainAccount<AddressData>[]>([]);
const selectedCollection = ref<string>();
const premium = usePremium();

watch([firstLimit, selectedAccounts, selectedCollection], () => {
  set(page, 1);
});

const nfts = computed<GalleryNft[]>(() => {
  const addresses: Nfts | null = get(perAccount);
  const value = get(prices);
  if (!addresses)
    return [];

  const allNfts: GalleryNft[] = [];
  for (const address in addresses) {
    const addressNfts: Nft[] = addresses[address];
    for (const nft of addressNfts) {
      const price = value[nft.tokenIdentifier];

      if (price?.manuallyInput) {
        const { priceAsset, priceInAsset, usdPrice: priceUsd } = price;
        allNfts.push({ ...nft, priceAsset, priceInAsset, priceUsd, address });
      }
      else {
        allNfts.push({ ...nft, address });
      }
    }
  }
  return allNfts;
});

const items = computed(() => {
  const accounts = get(selectedAccounts);
  const selection = get(selectedCollection);
  const hasAccounts = accounts.length > 0;
  const allNfts = [...get(nfts)];

  if (hasAccounts || selection) {
    return allNfts
      .filter(({ address, collection }) => {
        const sameAccount = hasAccounts ? accounts.find(account => getAccountAddress(account) === address) : true;
        const sameCollection = selection ? selection === collection.name : true;
        return sameAccount && sameCollection;
      })
      .sort((a, b) => sortNfts(sortBy, sortDescending, a, b));
  }

  return allNfts.sort((a, b) => sortNfts(sortBy, sortDescending, a, b));
});

const paginationData = computed({
  get() {
    return {
      page: get(page),
      total: get(items).length,
      limit: get(itemsPerPage),
      limits: get(limits),
    };
  },
  set(value: TablePaginationData) {
    set(page, value.page);
    set(itemsPerPage, value.limit);
  },
});

const visibleNfts = computed(() => {
  const perPage = get(itemsPerPage);
  const start = (get(page) - 1) * perPage;
  return get(items).slice(start, start + perPage);
});

const availableAddresses = computed(() => (get(perAccount) ? Object.keys(get(perAccount)!) : []));

const collections = computed(() => {
  if (!get(nfts))
    return [];

  return get(nfts)
    .map(({ collection }) => collection.name ?? '')
    .filter(uniqueStrings);
});

const { fetchNfts: nftFetch } = useNfts();

async function fetchNfts(ignoreCache = false) {
  set(loading, true);
  const { message, result } = await nftFetch(ignoreCache);
  if (result) {
    set(total, result.entriesFound);
    set(limit, result.entriesLimit);
    set(perAccount, result.addresses);
  }
  else {
    set(error, message);
  }
  set(loading, false);
}

const noData = computed(
  () => get(visibleNfts).length === 0 && !(get(selectedCollection) || get(selectedAccounts).length > 0),
);

const { fetchNftsPrices } = useAssetPricesApi();

async function fetchPrices() {
  try {
    const data = await fetchNftsPrices();
    set(prices, keyBy(data, 'asset'));
  }
  catch (error_: any) {
    set(priceError, error_.message);
  }
}

function updateSortBy(value: string) {
  assert(['name', 'priceUsd', 'collection'].includes(value));
  set(sortBy, value);
}

onMounted(fetchPrices);
onMounted(fetchNfts);

function sortNfts(
  sortBy: Ref<'name' | 'priceUsd' | 'collection'>,
  sortDesc: Ref<boolean>,
  a: GalleryNft,
  b: GalleryNft,
): number {
  const sortProp = get(sortBy);
  const desc = get(sortDesc);
  const isCollection = sortProp === 'collection';
  const aElement = isCollection ? a.collection.name : a[sortProp];
  const bElement = isCollection ? b.collection.name : b[sortProp];
  if (typeof aElement === 'string' && typeof bElement === 'string') {
    return desc
      ? bElement.localeCompare(aElement, 'en', { sensitivity: 'base' })
      : aElement.localeCompare(bElement, 'en', { sensitivity: 'base' });
  }
  else if (aElement instanceof BigNumber && bElement instanceof BigNumber) {
    return (desc ? bElement.minus(aElement) : aElement.minus(bElement)).toNumber();
  }
  else if (aElement === null && bElement === null) {
    return 0;
  }
  else if (aElement && !bElement) {
    return desc ? 1 : -1;
  }
  else if (!aElement && bElement) {
    return desc ? -1 : 1;
  }
  return 0;
}
</script>

<template>
  <ProgressScreen v-if="loading && visibleNfts.length === 0">
    {{ t('nft_gallery.loading') }}
  </ProgressScreen>
  <NoDataScreen
    v-else-if="noData"
    full
  >
    <template #title>
      {{ error ? t('nft_gallery.error_title') : t('nft_gallery.empty_title') }}
    </template>
    {{ error ? error : t('nft_gallery.empty_subtitle') }}
  </NoDataScreen>
  <TablePageLayout
    v-else
    class="p-4"
    :title="[t('navigation_menu.nfts')]"
  >
    <template #buttons>
      <div class="flex items-center gap-3">
        <NftImageRenderingSettingMenu />
        <ActiveModules :modules="modules" />
        <RefreshButton
          :loading="loading"
          :tooltip="t('nft_gallery.refresh_tooltip')"
          @refresh="fetchNfts(true)"
        />
      </div>
    </template>

    <div class="flex flex-col gap-6">
      <RuiCard>
        <div class="grid md:grid-cols-8 gap-4">
          <BlockchainAccountSelector
            v-model="selectedAccounts"
            class="md:col-span-3"
            :label="t('nft_gallery.select_account')"
            :chains="chains"
            dense
            outlined
            :usable-addresses="availableAddresses"
          />

          <NftCollectionSelector
            v-model="selectedCollection"
            class="md:col-span-3"
            :items="collections"
            variant="outlined"
            density="compact"
          />

          <NftSorter
            v-model:sort-desc="sortDescending"
            class="md:col-span-2"
            :sort-by="sortBy"
            @update:sort-by="updateSortBy($event)"
          />
        </div>
      </RuiCard>

      <RuiAlert
        v-if="!premium && visibleNfts.length > 0"
        type="info"
      >
        <i18n-t
          keypath="nft_gallery.upgrade"
          tag="span"
        >
          <template #limit>
            {{ limit }}
          </template>
          <template #link>
            <ExternalLink
              :text="t('upgrade_row.rotki_premium')"
              color="primary"
              premium
            />
          </template>
        </i18n-t>
      </RuiAlert>

      <div
        v-if="visibleNfts.length === 0"
        class="min-h-[60vh] flex justify-center items-center text-rui-text-secondary text-h6"
      >
        {{ t('nft_gallery.empty_filter') }}
      </div>
      <div
        v-else
        class="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 gap-4"
      >
        <div
          v-for="item in visibleNfts"
          :key="item.tokenIdentifier"
          class="overflow-hidden"
        >
          <NftGalleryItem :item="item" />
        </div>
      </div>
    </div>
    <RuiCard>
      <RuiTablePagination v-model="paginationData" />
    </RuiCard>
  </TablePageLayout>
</template>
