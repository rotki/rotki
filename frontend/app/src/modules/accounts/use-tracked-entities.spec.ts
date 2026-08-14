import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useTrackedEntities } from '@/modules/accounts/use-tracked-entities';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';

const state = {
  ready: ref(true),
};

vi.mock('@/modules/accounts/use-account-load-state', () => ({
  useAccountLoadState: (): object => ({ ready: state.ready }),
}));

describe('modules/accounts/useTrackedEntities', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    set(state.ready, true);
  });

  it('should report nothing tracked on an empty session', () => {
    const { loading, tracksNothing } = useTrackedEntities();

    expect(get(tracksNothing)).toBe(true);
    expect(get(loading)).toBe(false);
  });

  it('should count an account on any chain, not just an EVM one', () => {
    const { updateAccounts } = useBlockchainAccountsStore();
    const { tracksNothing } = useTrackedEntities();

    updateAccounts('btc', [createMock<BlockchainAccount>()]);

    expect(get(tracksNothing)).toBe(false);
  });

  it('should not count a chain that was read and came back empty', () => {
    const { updateAccounts } = useBlockchainAccountsStore();
    const { tracksNothing } = useTrackedEntities();

    updateAccounts('eth', []);

    expect(get(tracksNothing)).toBe(true);
  });

  it('should count a connected exchange on its own', () => {
    const { setConnectedExchanges } = useConnectedExchangesStore();
    const { tracksNothing } = useTrackedEntities();

    setConnectedExchanges([createMock<Exchange>()]);

    expect(get(tracksNothing)).toBe(false);
  });

  it('should count a manual balance or liability on its own', () => {
    const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
    const { tracksNothing } = useTrackedEntities();

    set(manualBalances, [createMock<ManualBalanceWithValue>()]);
    expect(get(tracksNothing)).toBe(false);

    set(manualBalances, []);
    set(manualLiabilities, [createMock<ManualBalanceWithValue>()]);
    expect(get(tracksNothing)).toBe(false);
  });

  it('should report loading until the accounts have been read', () => {
    set(state.ready, false);

    const { loading, tracksNothing } = useTrackedEntities();

    // the answer is still "nothing", it just cannot be trusted yet
    expect(get(tracksNothing)).toBe(true);
    expect(get(loading)).toBe(true);

    set(state.ready, true);

    expect(get(loading)).toBe(false);
  });
});
