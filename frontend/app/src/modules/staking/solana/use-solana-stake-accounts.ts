import type { ComputedRef, Ref } from 'vue';
import type { SolanaStakeAccount } from '@/modules/staking/staking-types';
import { type BigNumber, Zero } from '@rotki/common';
import { useSolanaStakingApi } from '@/modules/staking/api/use-solana-staking-api';

export interface SolanaStakeAccountRow extends SolanaStakeAccount {
  owner: string;
}

interface UseSolanaStakeAccountsReturn {
  error: Readonly<Ref<string>>;
  loading: Readonly<Ref<boolean>>;
  refresh: () => Promise<void>;
  rows: ComputedRef<SolanaStakeAccountRow[]>;
  total: ComputedRef<BigNumber>;
}

/**
 * Loads the stake accounts of every tracked Solana address.
 *
 * @remarks
 * A failed query keeps the rows of the last successful one and reports the failure through
 * `error`, so a flaky RPC does not blank a table the user was reading.
 */
export function useSolanaStakeAccounts(): UseSolanaStakeAccountsReturn {
  const { fetchStakeAccounts } = useSolanaStakingApi();

  const rows = shallowRef<SolanaStakeAccountRow[]>([]);
  const loading = shallowRef<boolean>(false);
  const error = shallowRef<string>('');

  const total = computed<BigNumber>(() => get(rows).reduce<BigNumber>((acc, { amount }) => acc.plus(amount), Zero));

  async function refresh(): Promise<void> {
    set(loading, true);
    set(error, '');
    try {
      const accounts = await fetchStakeAccounts();
      set(rows, Object.entries(accounts).flatMap(([owner, stakeAccounts]) =>
        stakeAccounts.map(stakeAccount => ({ ...stakeAccount, owner }))));
    }
    catch (error_: unknown) {
      set(error, error_ instanceof Error ? error_.message : String(error_));
    }
    finally {
      set(loading, false);
    }
  }

  return {
    error: readonly(error),
    loading: readonly(loading),
    refresh,
    rows: computed<SolanaStakeAccountRow[]>(() => get(rows)),
    total,
  };
}
