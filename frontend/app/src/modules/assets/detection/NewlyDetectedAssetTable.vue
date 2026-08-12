<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { Filters } from '@/modules/assets/detection/use-newly-detected-filter';
import { type BigNumber, getAddressFromEvmIdentifier, getAddressFromSolanaIdentifier } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useNewlyDetectedFields } from '@/modules/assets/detection/use-newly-detected-fields';
import { useNewlyDetectedSelection } from '@/modules/assets/detection/use-newly-detected-selection';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useServerTable } from '@/modules/core/table/use-server-table';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { getTokenChain } from './get-token-chain';
import NewlyDetectedAssetRowActions from './NewlyDetectedAssetRowActions.vue';
import NewlyDetectedAssetToolbar from './NewlyDetectedAssetToolbar.vue';
import { type NewDetectedToken, NewDetectedTokenKind, type NewDetectedTokensRequestPayload } from './types';
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

const { getData, isReady } = useNewlyDetectedTokens();
const { allEvmChains } = useSupportedChains();
const { getAssetPrice } = usePriceUtils();

const fields = useNewlyDetectedFields();

const {
  collection,
  filter,
  isLoading,
  pagination,
  refetch,
  sort,
} = useServerTable<NewDetectedToken, NewDetectedTokensRequestPayload, Filters>({
  fetch: getData,
  fields,
  sort: {
    default: {
      column: 'detectedAt',
      direction: 'desc',
    },
  },
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
  return get(collection).data.map(data => ({
    ...data,
    address: TOKEN_KIND_MAPPING[data.tokenKind].addressFormatter(data.tokenIdentifier),
    chain: getTokenChain(data, evmChains),
    price: getAssetPrice(data.tokenIdentifier),
  }));
});

const {
  allSelected,
  markAsSpam,
  modelSelected,
  removeTokens,
  toggleSelection,
} = useNewlyDetectedSelection({
  filters: filter,
  found: (): number => get(collection).found,
  refetch,
});

watch(isReady, (ready) => {
  if (ready)
    refetch();
});

onMounted(async () => {
  await refetch();
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
          v-model:filters="filter"
          :all-selected="allSelected"
          :selected-count="modelSelected.length"
          :found="collection.found"
          :fields="fields"
          @toggle-selection="toggleSelection()"
          @accept="removeTokens()"
          @mark-spam="markAsSpam()"
        />
      </template>

      <RuiDataTable
        v-model="modelSelected"
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
