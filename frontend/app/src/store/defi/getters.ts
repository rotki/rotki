import { default as BigNumber } from 'bignumber.js';
import { GetterTree } from 'vuex';
import { DefiState } from '@/store/defi/state';
import { MakerDAOVaultModel, MakerDAOVaultSummary } from '@/store/defi/types';
import { RotkehlchenState } from '@/store/store';
import { AccountDSRMovement, DSRBalance } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

export const getters: GetterTree<DefiState, RotkehlchenState> = {
  dsrBalances: ({ dsrBalances }: DefiState): DSRBalance[] => {
    const { balances } = dsrBalances;
    return Object.keys(balances).map(address => ({
      address,
      balance: balances[address]
    }));
  },

  currentDSR: ({ dsrBalances }: DefiState): BigNumber => {
    return dsrBalances.currentDSR;
  },

  totalGain: ({ dsrHistory }: DefiState): BigNumber => {
    return Object.keys(dsrHistory)
      .map(account => dsrHistory[account])
      .reduce((sum, account) => sum.plus(account.gainSoFar), Zero);
  },

  accountGain: ({ dsrHistory }: DefiState) => (account: string): BigNumber => {
    return dsrHistory[account]?.gainSoFar ?? Zero;
  },

  accountGainUsdValue: ({ dsrHistory }: DefiState) => (
    account: string
  ): BigNumber => {
    return dsrHistory[account]?.gainSoFarUsdValue ?? Zero;
  },

  dsrHistory: ({ dsrHistory }: DefiState): AccountDSRMovement[] => {
    return Object.keys(dsrHistory).reduce((acc, address) => {
      const { movements } = dsrHistory[address];
      acc.push(
        ...movements.map(movement => ({
          address,
          ...movement
        }))
      );
      return acc;
    }, new Array<AccountDSRMovement>());
  },

  makerDAOVaults: ({
    makerDAOVaults,
    makerDAOVaultDetails
  }: DefiState): MakerDAOVaultModel[] => {
    const vaults: MakerDAOVaultModel[] = [];
    for (let i = 0; i < makerDAOVaults.length; i++) {
      const vault = makerDAOVaults[i];
      const details = makerDAOVaultDetails.find(
        details => details.identifier === vault.identifier
      );
      vaults.push(details ? { ...vault, ...details } : vault);
    }
    return vaults;
  },

  makerDAOVaultSummary: ({
    makerDAOVaults
  }: DefiState): MakerDAOVaultSummary => {
    const totalCollateralUsd = makerDAOVaults
      .map(vault => vault.collateralUsdValue)
      .reduce((sum, collateralUsdValue) => sum.plus(collateralUsdValue), Zero);
    const totalDebt = makerDAOVaults
      .map(vault => vault.debtValue)
      .reduce((sum, debt) => sum.plus(debt), Zero);
    return { totalCollateralUsd, totalDebt };
  },

  loanWatchers: ({ watchers }) => {
    const loanWatcherTypes = ['makervault_collateralization_ratio'];

    return watchers.filter(
      watcher => loanWatcherTypes.indexOf(watcher.type) > -1
    );
  }
};
