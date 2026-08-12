import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type {
  EthereumValidator,
  EthereumValidatorRequestPayload,
} from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/staking/eth/use-eth-validator-filter';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useSetting } from '@/modules/settings/use-setting';
import { useEthValidatorFields } from '@/modules/staking/eth/use-eth-validator-fields';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

interface UseEthValidatorDataReturn {
  cols: ComputedRef<DataTableColumn<EthereumValidator>[]>;
  ethStakingValidators: ComputedRef<EthereumValidator[]>;
  /** The pill-bar fields, built here because the table's url shape is read off them. */
  fields: ComputedRef<FieldDef[]>;
  fetchData: () => Promise<void>;
  filters: WritableComputedRef<Filters>;
  pagination: Ref<TablePaginationData>;
  rows: Ref<Collection<EthereumValidator>>;
  modelSelected: Ref<number[]>;
  sort: Ref<DataTableSortData<EthereumValidator>>;
}

export function useEthValidatorData(): UseEthValidatorDataReturn {
  const { t } = useI18n({ useScope: 'global' });
  const modelSelected = ref<number[]>([]);

  const blockchainValidatorsStore = useBlockchainValidatorsStore();
  const { fetchValidators } = blockchainValidatorsStore;
  const { ethStakingValidators } = storeToRefs(blockchainValidatorsStore);
  const currencySymbol = useSetting('currencySymbol');

  const fields = useEthValidatorFields();

  const {
    collection: rows,
    filter: filters,
    pagination,
    refetch: fetchData,
    sort,
  } = useServerTable<
    EthereumValidator,
    EthereumValidatorRequestPayload,
    Filters
  >({
    fetch: fetchValidators,
    fields,
    sort: {
      default: {
        column: 'index',
        direction: 'desc',
      },
    },
    urlState: { mode: 'route' },
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
    fields,
    fetchData,
    filters,
    pagination,
    rows,
    modelSelected,
    sort,
  };
}
