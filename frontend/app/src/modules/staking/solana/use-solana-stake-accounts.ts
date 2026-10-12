import { type BigNumber, Zero } from '@rotki/common';
import { useStakingApi } from '@/modules/staking/api/use-staking-api';
import { type SolanaStakeAccount, SolanaStakeAccountsSchema } from '@/modules/staking/staking-types';
import { useStakingRows, type UseStakingRowsReturn } from '@/modules/staking/use-staking-rows';
import { ActivityPart } from '@/modules/task-center/core/types';

export interface SolanaStakeAccountRow extends SolanaStakeAccount {
  owner: string;
}

type UseSolanaStakeAccountsReturn = UseStakingRowsReturn<SolanaStakeAccountRow, BigNumber>;

/** Loads the stake accounts of every tracked Solana address. */
export function useSolanaStakeAccounts(): UseSolanaStakeAccountsReturn {
  const { fetchSolanaStakeAccounts } = useStakingApi();

  return useStakingRows({
    parse: result => SolanaStakeAccountsSchema.parse(result),
    part: ActivityPart.SOLANA,
    query: fetchSolanaStakeAccounts,
    toRows: ({ accounts }) => Object.entries(accounts).flatMap(([owner, stakeAccounts]) =>
      stakeAccounts.map(stakeAccount => ({ ...stakeAccount, owner }))),
    toTotal: rows => rows.reduce<BigNumber>((acc, { amount }) => acc.plus(amount), Zero),
  });
}
