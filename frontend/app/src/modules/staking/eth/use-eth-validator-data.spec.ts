import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, type Ref } from 'vue';
import { TableId } from '@/modules/core/table/use-remember-table-sorting';
import { useEthValidatorData } from '@/modules/staking/eth/use-eth-validator-data';

function validator(index: number): EthereumValidator {
  return {
    amount: bigNumberify(32),
    index,
    publicKey: '0xabc',
    status: 'active',
    type: 'validator',
    value: bigNumberify(64000),
  };
}

const mockFetchData = vi.fn();
const mockFetchValidators = vi.fn();
const mockRememberSorting = vi.fn();
const mockEthStakingValidators = ref<EthereumValidator[]>([]);
const mockCurrencySymbol = ref<string>('USD');
const mockFilters = ref({});
const mockMatchers = ref([]);
const mockPagination = ref({});
const mockSort = ref({ column: 'index', direction: 'desc' });
const mockRows = ref({ data: [], found: 0, limit: 10, total: 0 });

vi.mock('vue-i18n', async importOriginal => ({
  ...await importOriginal<typeof import('vue-i18n')>(),
  useI18n: (): { t: (key: string, args?: { symbol?: string }) => string } => ({
    t: (key: string, args?: { symbol?: string }): string => (args ? `${key}:${args.symbol}` : key),
  }),
}));

vi.mock('@/modules/staking/use-blockchain-validators-store', () => ({
  useBlockchainValidatorsStore: (): {
    ethStakingValidators: Ref<EthereumValidator[]>;
    fetchValidators: typeof mockFetchValidators;
  } => ({
    ethStakingValidators: mockEthStakingValidators,
    fetchValidators: mockFetchValidators,
  }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => mockCurrencySymbol),
}));

vi.mock('@/modules/core/table/use-remember-table-sorting', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-remember-table-sorting')>(),
  useRememberTableSorting: (...args: unknown[]): void => mockRememberSorting(...args),
}));

vi.mock('@/modules/core/table/use-pagination-filter', () => ({
  usePaginationFilters: (): Record<string, unknown> => ({
    fetchData: mockFetchData,
    filters: mockFilters,
    matchers: mockMatchers,
    pagination: mockPagination,
    sort: mockSort,
    state: mockRows,
  }),
}));

describe('useEthValidatorData', () => {
  let scope: EffectScope | undefined;

  function create(): ReturnType<typeof useEthValidatorData> {
    scope = effectScope();
    const result = scope.run(() => useEthValidatorData());
    assert(result);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(mockEthStakingValidators, []);
    set(mockCurrencySymbol, 'USD');
  });

  afterEach(() => {
    scope?.stop();
    scope = undefined;
  });

  it('should expose seven columns in order', () => {
    const { cols } = create();
    expect(get(cols).map(col => col.key)).toEqual([
      'index',
      'publicKey',
      'status',
      'amount',
      'value',
      'ownershipPercentage',
      'actions',
    ]);
  });

  it('should label the value column with the current currency symbol', () => {
    set(mockCurrencySymbol, 'EUR');
    const { cols } = create();
    const valueCol = get(cols).find(col => col.key === 'value');
    expect(valueCol?.label).toBe('common.value_in_symbol:EUR');
  });

  it('should mark all columns except ownership and actions as sortable', () => {
    const { cols } = create();
    const sortable = Object.fromEntries(get(cols).map(col => [col.key, col.sortable ?? false]));
    expect(sortable.ownershipPercentage).toBe(false);
    expect(sortable.actions).toBe(false);
    expect(sortable.index).toBe(true);
  });

  it('should pass through pagination state from the paginator', () => {
    const data = create();
    expect(data.fetchData).toBe(mockFetchData);
    expect(data.filters).toBe(mockFilters);
    expect(data.matchers).toBe(mockMatchers);
    expect(data.pagination).toBe(mockPagination);
    expect(data.sort).toBe(mockSort);
    expect(data.rows).toBe(mockRows);
  });

  it('should expose the validators from the store', () => {
    const validators = [validator(7)];
    set(mockEthStakingValidators, validators);
    const data = create();
    expect(get(data.ethStakingValidators)).toStrictEqual(validators);
  });

  it('should start with no selection', () => {
    const { modelSelected } = create();
    expect(get(modelSelected)).toEqual([]);
  });

  it('should register table sorting for the validators table', () => {
    create();
    expect(mockRememberSorting).toHaveBeenCalledWith(TableId.ETH_STAKING_VALIDATORS, mockSort, expect.anything());
  });

  it('should fetch immediately and again whenever the validators change', async () => {
    create();
    expect(mockFetchData).toHaveBeenCalledTimes(1);

    set(mockEthStakingValidators, [validator(1)]);
    await nextTick();

    expect(mockFetchData).toHaveBeenCalledTimes(2);
  });
});
