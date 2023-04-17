import { type Balance, type HasBalance } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Eth2Validators } from '@rotki/common/lib/staking/eth2';
import { type ComputedRef } from 'vue';
import { type Writeable } from '@/types';
import { type AccountAssetBalances } from '@/types/balances';
import {
  type BlockchainTotal,
  type SubBlockchainTotal
} from '@/types/blockchain';
import { type BlockchainAssetBalances } from '@/types/blockchain/balances';
import { L2_LOOPRING } from '@/types/protocols';
import { Section } from '@/types/status';
import { ReadOnlyTag } from '@/types/tags';
import {
  type AccountWithBalance,
  type AccountWithBalanceAndSharedOwnership,
  type AssetBreakdown,
  type BlockchainAccountWithBalance
} from '@/types/blockchain/accounts';

function addLoopringBreakdown(
  loopring: AccountAssetBalances,
  ethBreakdown: AssetBreakdown[],
  asset: string
): void {
  const loopringBalances = get(loopring);
  for (const address in loopringBalances) {
    const existing: Writeable<AssetBreakdown> | undefined = ethBreakdown.find(
      value => value.address === address
    );
    const balanceElement = loopringBalances[address][asset];
    if (!balanceElement) {
      continue;
    }
    if (existing) {
      existing.balance = balanceSum(existing.balance, balanceElement);
    } else {
      ethBreakdown.push({
        address,
        location: Blockchain.ETH,
        balance: loopringBalances[address][asset],
        tags: [ReadOnlyTag.LOOPRING]
      });
    }
  }
}

const addEth2Breakdown = (
  asset: string,
  validators: Eth2Validators,
  balances: BlockchainAssetBalances,
  ethBreakdown: AssetBreakdown[],
  treatEth2AsEth: boolean
): void => {
  if (
    asset === Blockchain.ETH2 ||
    (treatEth2AsEth && asset === Blockchain.ETH)
  ) {
    for (const { publicKey } of validators.entries) {
      const validatorBalances = balances[publicKey];
      let balance: Balance = zeroBalance();
      if (validatorBalances && validatorBalances.assets) {
        const assets = validatorBalances.assets;
        balance = {
          amount: assets[Blockchain.ETH2].amount,
          usdValue: assetSum(assets)
        };
      }

      ethBreakdown.push({
        address: publicKey,
        location: Blockchain.ETH2,
        balance,
        tags: []
      });
    }
  }
};

export const useEthAccountBalances = () => {
  const { balances, loopring } = storeToRefs(useEthBalancesStore());
  const { eth, eth2Validators } = storeToRefs(useEthAccountsStore());
  const { treatEth2AsEth } = storeToRefs(useGeneralSettingsStore());

  const ethAccounts: ComputedRef<AccountWithBalance[]> = computed(() => {
    const accounts = accountsWithBalances(
      get(eth),
      get(balances).ETH,
      Blockchain.ETH
    );

    return accounts.map(ethAccount => {
      const address = ethAccount.address;
      const tags = ethAccount.tags ? [...ethAccount.tags] : [];

      // check if account have loopring balances
      const loopringAssetBalances = get(loopring)[address];
      if (loopringAssetBalances) {
        tags.push(ReadOnlyTag.LOOPRING);
      }

      return {
        ...ethAccount,
        tags: tags.filter(uniqueStrings)
      };
    });
  });

  const eth2Accounts: ComputedRef<AccountWithBalanceAndSharedOwnership[]> =
    computed(() => {
      const accounts: AccountWithBalanceAndSharedOwnership[] = [];
      const state = get(balances).ETH2;

      for (const { publicKey, validatorIndex, ownershipPercentage } of get(
        eth2Validators
      ).entries) {
        const validatorBalances = state[publicKey];
        let balance: Balance = zeroBalance();
        if (validatorBalances && validatorBalances.assets) {
          const assets = validatorBalances.assets;
          balance = {
            amount: assets[Blockchain.ETH2].amount,
            usdValue: assetSum(assets)
          };
        }
        accounts.push({
          address: publicKey,
          chain: Blockchain.ETH2,
          balance,
          label: validatorIndex.toString() ?? '',
          tags: [],
          ownershipPercentage
        });
      }
      return accounts;
    });

  const loopringAccounts: ComputedRef<BlockchainAccountWithBalance[]> =
    computed(() => {
      const accounts: BlockchainAccountWithBalance[] = [];
      const loopringBalances = get(loopring);
      const ethAccounts = get(eth);
      for (const address in loopringBalances) {
        const assets = loopringBalances[address];

        const tags =
          ethAccounts.find(account => account.address === address)?.tags || [];

        const balance = zeroBalance();

        for (const asset in assets) {
          const assetBalance = assets[asset];
          const sum = balanceSum(balance, assetBalance);
          balance.amount = sum.amount;
          balance.usdValue = sum.usdValue;
        }

        accounts.push({
          address,
          balance,
          chain: Blockchain.ETH,
          label: '',
          tags: [...tags, ReadOnlyTag.LOOPRING].filter(uniqueStrings)
        });
      }
      return accounts;
    });

  const { shouldShowLoadingScreen } = useStatusStore();

  const loopringSum: ComputedRef<HasBalance[]> = computed(() => {
    const balances: Record<string, HasBalance> = {};
    const loopringBalances = get(loopring);
    if (Object.keys(loopringBalances).length <= 0) {
      return [];
    }
    for (const address in loopringBalances) {
      for (const asset in loopringBalances[address]) {
        if (!balances[asset]) {
          balances[asset] = {
            balance: loopringBalances[address][asset]
          };
        } else {
          balances[asset] = {
            balance: balanceSum(
              loopringBalances[address][asset],
              balances[asset].balance
            )
          };
        }
      }
    }
    return Object.values(balances);
  });

  const ethChildrenTotals: ComputedRef<SubBlockchainTotal[]> = computed(() => [
    {
      protocol: L2_LOOPRING,
      usdValue: sum(get(loopringSum)),
      loading: get(shouldShowLoadingScreen(Section.L2_LOOPRING_BALANCES))
    }
  ]);

  const ethTotals: ComputedRef<BlockchainTotal[]> = computed(() => [
    {
      chain: Blockchain.ETH,
      children: get(ethChildrenTotals).filter((item: SubBlockchainTotal) =>
        item.usdValue.gt(0)
      ),
      usdValue: sum(get(ethAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN_ETH))
    },
    {
      chain: Blockchain.ETH2,
      children: [],
      usdValue: sum(get(eth2Accounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN_ETH2))
    }
  ]);

  const getBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> =>
    computed(() => {
      const ethBreakdown = getBlockchainBreakdown(
        Blockchain.ETH,
        get(balances).ETH,
        get(eth),
        asset
      );

      addLoopringBreakdown(get(loopring), ethBreakdown, asset);
      addEth2Breakdown(
        asset,
        get(eth2Validators),
        get(balances).ETH2,
        ethBreakdown,
        get(treatEth2AsEth)
      );
      return [...ethBreakdown];
    });

  return {
    ethAccounts,
    eth2Accounts,
    loopringAccounts,
    ethTotals,
    getBreakdown
  };
};
