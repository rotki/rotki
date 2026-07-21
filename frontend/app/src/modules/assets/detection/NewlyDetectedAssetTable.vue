<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import { type BigNumber, getAddressFromEvmIdentifier, getAddressFromSolanaIdentifier } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { arrayify } from '@/modules/core/common/data/array';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { getTokenChain } from './get-token-chain';
import NewlyDetectedAssetRowActions from './NewlyDetectedAssetRowActions.vue';
import NewlyDetectedAssetToolbar from './NewlyDetectedAssetToolbar.vue';
import { type NewDetectedToken, NewDetectedTokenKind } from './types';
import { useNewlyDetectedTokens } from './use-newly-detected-tokens';

defineOptions({
  name: 'NewlyDetectedAssetTable',
});

interface Token extends NewDetectedToken {
  address: string;
  chain: string;
  price?: BigNumber;
}

const TOKEN_KIND_MAPPING = {
  [NewDetectedTokenKind.EVM]: {
    addressFormatter: getAddressFromEvmIdentifier,
  },
  [NewDetectedTokenKind.SOLANA]: {
    addressFormatter: getAddressFromSolanaIdentifier,
  },
} as const;

const { t } = useI18n({ useScope: 'global' });

const selected = ref<string[]>([]);
const tokenKindFilter = ref<NewDetectedTokenKind>();

const { getAllIdentifiers, getData, isReady, removeNewDetectedTokens } = useNewlyDetectedTokens();
const { allEvmChains, isSolanaChains } = useSupportedChains();
const { addresses } = useAccountAddresses();
const { markAssetsAsSpam } = useSpamAsset();
const { getAssetPrice } = usePriceUtils();

const {
  fetchData,
  isLoading,
  pagination,
  sort,
  state,
} = usePaginationFilters<NewDetectedToken>(getData, {
  defaultSortBy: {
    column: 'detectedAt',
    direction: 'desc',
  },
  extraParams: computed(() => ({
    tokenKind: get(tokenKindFilter),
  })),
});

const cols = computed<DataTableColumn<Token>[]>(() => [
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'tokenIdentifier',
    label: t('common.asset'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'address',
    label: t('common.address'),
    sortable: false,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'price',
    label: t('common.price'),
    sortable: false,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'detectedAt',
    label: t('asset_table.newly_detected.detected_at'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'description',
    label: t('asset_table.newly_detected.seen_during'),
  },
  {
    align: 'center',
    cellClass: 'py-0',
    class: 'py-0',
    key: 'actions',
    label: t('common.actions_text'),
  },
]);

useRememberTableSorting<Token>(TableId.NEWLY_DETECTED_ASSETS, sort, cols);

const rows = computed<Token[]>(() => {
  const evmChains = get(allEvmChains);
  return get(state).data.map(data => ({
    ...data,
    address: TOKEN_KIND_MAPPING[data.tokenKind].addressFormatter(data.tokenIdentifier),
    chain: getTokenChain(data, evmChains),
    price: getAssetPrice(data.tokenIdentifier),
  }));
});

const allSelected = computed<boolean>(() => {
  const selectionLength = get(selected).length;
  const totalFiltered = get(state).found;
  return selectionLength > 0 && totalFiltered === selectionLength;
});

const hasSolanaAccounts = computed<boolean>(() =>
  Object.entries(get(addresses)).some(([chain, addrs]) => isSolanaChains(chain) && addrs.length > 0),
);

const tokenKindOptions = computed<{ title: string; value: NewDetectedTokenKind | undefined }[]>(() => {
  const options: { title: string; value: NewDetectedTokenKind | undefined }[] = [
    { title: 'EVM', value: NewDetectedTokenKind.EVM },
  ];

  if (get(hasSolanaAccounts)) {
    options.unshift({ title: t('asset_table.newly_detected.all_types'), value: undefined });
    options.push({ title: 'Solana', value: NewDetectedTokenKind.SOLANA });
  }

  return options;
});

async function toggleSelection(): Promise<void> {
  const selectedLength = get(selected).length;
  const allIdentifiers = await getAllIdentifiers(get(tokenKindFilter));

  if (selectedLength === allIdentifiers.length)
    set(selected, []);
  else
    set(selected, allIdentifiers);
}

function getIdentifiers(identifiers?: string | string[]): string[] {
  return identifiers
    ? arrayify(identifiers)
    : get(selected);
}

function getUniqueIds(identifiers?: string | string[]): string[] {
  return getIdentifiers(identifiers).filter(uniqueStrings);
}

async function removeTokens(identifiers?: string | string[]): Promise<void> {
  await removeNewDetectedTokens(getIdentifiers(identifiers));
  set(selected, []);
  await fetchData();
}

async function markAsSpam(identifiers?: string | string[]): Promise<void> {
  const ids = getUniqueIds(identifiers);

  const status = await markAssetsAsSpam(ids);

  if (status.success)
    await removeTokens(ids);
}

watch(isReady, (ready) => {
  if (ready)
    fetchData();
});

watchImmediate(hasSolanaAccounts, (hasSolana) => {
  if (!hasSolana)
    set(tokenKindFilter, NewDetectedTokenKind.EVM);
});

watch(tokenKindFilter, () => {
  set(selected, []);
});

onMounted(async () => {
  await fetchData();
});
</script>

<template>
  <TablePageLayout
    child
    hide-header
    class="lg:!-mt-5"
  >
    <RuiCard>
      <template #custom-header>
        <NewlyDetectedAssetToolbar
          v-model="tokenKindFilter"
          :all-selected="allSelected"
          :selected-count="selected.length"
          :found="state.found"
          :token-kind-options="tokenKindOptions"
          @toggle-selection="toggleSelection()"
          @accept="removeTokens()"
          @mark-spam="markAsSpam()"
        />
      </template>

      <RuiDataTable
        v-model="selected"
        v-model:sort.external="sort"
        v-model:pagination.external="pagination"
        :cols="cols"
        :rows="rows"
        :loading="isLoading"
        outlined
        dense
        row-attr="tokenIdentifier"
      >
        <template #item.tokenIdentifier="{ row }">
          <AssetDetails
            hide-menu
            :asset="row.tokenIdentifier"
          />
        </template>

        <template #item.address="{ row }">
          <HashLink
            :location="row.chain"
            :text="row.address"
            type="token"
          />
        </template>

        <template #item.price="{ row }">
          <FiatDisplay
            :value="row.price"
            :price-asset="row.tokenIdentifier"
          />
        </template>

        <template #item.detectedAt="{ row }">
          <DateDisplay
            :timestamp="row.detectedAt"
            milliseconds
          />
        </template>

        <template #item.description="{ row }">
          <div v-if="row.seenDescription">
            {{ row.seenDescription }}
          </div>

          <div v-if="row.seenTxReference">
            <HashLink
              :location="row.chain"
              :text="row.seenTxReference"
              type="transaction"
            />
          </div>
        </template>

        <template #item.actions="{ row }">
          <NewlyDetectedAssetRowActions
            :key="row.tokenIdentifier"
            @accept="removeTokens(row.tokenIdentifier)"
            @mark-spam="markAsSpam(row.tokenIdentifier)"
          />
        </template>
      </RuiDataTable>
    </RuiCard>
  </TablePageLayout>
</template>
