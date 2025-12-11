import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type {
  EthereumValidator,
  EthereumValidatorRequestPayload,
} from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import { type Filters, type Matcher, useEthValidatorAccountFilter } from '@/composables/filters/eth-validator';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { useGeneralSettingsStore } from '@/store/settings/general';

interface UseEthValidatorDataReturn {
  cols: ComputedRef<DataTableColumn<EthereumValidator>[]>;
  ethStakingValidators: ComputedRef<EthereumValidator[]>;
  fetchData: () => Promise<void>;
  filters: WritableComputedRef<Filters>;
  matchers: ComputedRef<Matcher[]>;
  pagination: Ref<TablePaginationData>;
  rows: Ref<Collection<EthereumValidator>>;
  selected: Ref<number[]>;
  sort: Ref<DataTableSortData<EthereumValidator>>;
}

export function useEthValidatorData(): UseEthValidatorDataReturn {
  const { t } = useI18n({ useScope: 'global' });
  const selected = ref<number[]>([]);

  const blockchainValidatorsStore = useBlockchainValidatorsStore();
  const { fetchValidators } = blockchainValidatorsStore;
  const { ethStakingValidators } = storeToRefs(blockchainValidatorsStore);
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  const {
    fetchData,
    filters,
    matchers,
    pagination,
    sort,
    state: rows,
  } = usePaginationFilters<
    EthereumValidator,
    EthereumValidatorRequestPayload,
    Filters,
    Matcher
  >(fetchValidators, {
    defaultSortBy: {
      column: 'index',
      direction: 'desc',
    },
    filterSchema: () => useEthValidatorAccountFilter(t),
    history: 'router',
  });

  const cols = computed<DataTableColumn<EthereumValidator>[]>(() => {
    const currency = { symbol: get(currencySymbol) };
    return [
      {
        cellClass: 'py-0',
        key: 'index',
        label: t('common.validator_index'),
        sortable: true,
      },
      {
        cellClass: 'py-0',
        key: 'publicKey',
        label: t('eth2_input.public_key'),
        sortable: true,
      },
      {
        cellClass: 'py-0',
        key: 'status',
        label: t('common.status'),
        sortable: true,
      },
      {
        align: 'end',
        cellClass: 'py-0',
        key: 'amount',
        label: t('common.amount'),
        sortable: true,
      },
      {
        align: 'end',
        cellClass: 'py-0',
        key: 'value',
        label: t('common.value_in_symbol', currency),
        sortable: true,
      },
      {
        align: 'end',
        cellClass: 'py-0',
        key: 'ownershipPercentage',
        label: t('common.ownership'),
        sortable: false,
      },
      {
        align: 'end',
        cellClass: '!p-0',
        key: 'actions',
        label: t('common.actions_text'),
      },
    ];
  });

  useRememberTableSorting<EthereumValidator>(TableId.ETH_STAKING_VALIDATORS, sort, cols);

  watchImmediate(ethStakingValidators, async () => {
    await fetchData();
  });

  return {
    cols,
    ethStakingValidators,
    fetchData,
    filters,
    matchers,
    pagination,
    rows,
    selected,
    sort,
  };
}
