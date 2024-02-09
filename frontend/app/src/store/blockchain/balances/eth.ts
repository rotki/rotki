import { Blockchain } from '@rotki/common/lib/blockchain';
import { AccountAssetBalances, type AssetBalances } from '@/types/balances';
import { type EthChains, isEthChain } from '@/types/blockchain/chains';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { StakingBalance } from '@rotki/common/lib/staking/eth2';
import type { MaybeRef } from '@vueuse/core';
import type { BigNumber } from '@rotki/common';
import type {
  BlockchainAssetBalances,
  BlockchainBalances,
} from '@/types/blockchain/balances';
import type { AssetPrices } from '@/types/prices';
import type { TaskMeta } from '@/types/task';

type Totals = Record<EthChains, AssetBalances>;

type Balances = Record<EthChains, BlockchainAssetBalances>;

function defaultTotals(): Totals {
  return {
    [Blockchain.ETH]: {},
    [Blockchain.ETH2]: {},
  };
}

function defaultBalances(): Balances {
  return {
    [Blockchain.ETH]: {},
    [Blockchain.ETH2]: {},
  };
}

export const useEthBalancesStore = defineStore('balances/eth', () => {
  const loopring: Ref<AccountAssetBalances> = ref({});

  const balances: Ref<Balances> = ref(defaultBalances());
  const totals: Ref<Totals> = ref(defaultTotals());
  const liabilities: Ref<Totals> = ref(defaultTotals());

  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { queryLoopringBalances } = useBlockchainBalancesApi();
  const { t } = useI18n();

  const stakingBalances = computed<StakingBalance[]>(() => {
    const balancesRef = get(balances);
    const ethStakingBalances = balancesRef[Blockchain.ETH2];
    if (Object.keys(ethStakingBalances).length === 0)
      return [];

    return Object.entries(ethStakingBalances).map(([publicKey, balance]) => {
      const ETH2_ASSET = Blockchain.ETH2.toUpperCase();
      return {
        publicKey,
        ...balance.assets[ETH2_ASSET],
      };
    });
  });

  const getLoopringAssetBalances = (
    address: MaybeRef<string> = ref(''),
  ): ComputedRef<AssetBalances> =>
    computed(() => {
      const ownedAssets: AssetBalances = {};
      const accountAddress = get(address);

      const balances = get(loopring);
      for (const [address, assets] of Object.entries(balances)) {
        if (accountAddress && accountAddress !== address)
          continue;

        for (const [asset, value] of Object.entries(assets)) {
          const identifier = getAssociatedAssetIdentifier(asset);
          const associatedAsset: string = get(identifier);
          const ownedAsset = ownedAssets[associatedAsset];

          if (!ownedAsset)
            ownedAssets[associatedAsset] = { ...value };
          else
            ownedAssets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
        }
      }
      return ownedAssets;
    });

  const fetchLoopringBalances = async (refresh: boolean) => {
    if (!get(activeModules).includes(Module.LOOPRING))
      return;

    const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(
      Section.L2_LOOPRING_BALANCES,
    );

    if (fetchDisabled(refresh))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);
    try {
      const taskType = TaskType.L2_LOOPRING;
      const { taskId } = await queryLoopringBalances();
      const { result } = await awaitTask<AccountAssetBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.balances.loopring.task.title'),
        },
      );

      set(loopring, AccountAssetBalances.parse(result));
      setStatus(Status.LOADED);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.balances.loopring.error.title'),
          message: t('actions.balances.loopring.error.description', {
            error: error.message,
          }),
          display: true,
        });
      }
      resetStatus();
    }
  };

  const update = (
    chain: Blockchain,
    { perAccount, totals: updatedTotals }: BlockchainBalances,
  ) => {
    if (!isEthChain(chain))
      return;

    set(balances, {
      ...get(balances),
      [chain]: perAccount[chain] ?? {},
    });

    set(totals, {
      ...get(totals),
      [chain]: removeZeroAssets(updatedTotals.assets),
    });

    set(liabilities, {
      ...get(liabilities),
      [chain]: removeZeroAssets(updatedTotals.liabilities),
    });
  };

  const updatePrices = (prices: MaybeRef<AssetPrices>) => {
    set(totals, updateTotalsPrices(totals, prices));
    set(liabilities, updateTotalsPrices(liabilities, prices));
    set(balances, updateBlockchainAssetBalances(balances, prices));
    set(loopring, updateAssetBalances(loopring, prices));
  };

  /**
   * Adjusts the balances for an ethereum staking validator based on the percentage of ownership.
   *
   * @param publicKey the validator's public key is used to identify the balance
   * @param oldOwnershipPercentage the ownership of the validator before the edit
   * @param newOwnershipPercentage the ownership percentage of the validator after the edit
   */
  const updateEthStakingOwnership = (
    publicKey: string,
    oldOwnershipPercentage: BigNumber,
    newOwnershipPercentage: BigNumber,
  ): void => {
    const { eth2 } = get(balances);
    if (!eth2[publicKey])
      return;

    const ETH2_ASSET = Blockchain.ETH2.toUpperCase();

    const { amount, usdValue } = eth2[publicKey].assets[ETH2_ASSET];

    // we should not need to update anything if amount and value are zero
    if (amount.isZero() && usdValue.isZero())
      return;

    const calc = (
      value: BigNumber,
      oldPercentage: BigNumber,
      newPercentage: BigNumber,
    ): BigNumber => value.dividedBy(oldPercentage).multipliedBy(newPercentage);

    const newAmount = calc(
      amount,
      oldOwnershipPercentage,
      newOwnershipPercentage,
    );

    const newValue = calc(
      usdValue,
      oldOwnershipPercentage,
      newOwnershipPercentage,
    );

    const amountDiff = amount.minus(newAmount);
    const valueDiff = usdValue.minus(newValue);

    set(balances, {
      ...get(balances),
      [Blockchain.ETH2]: {
        ...eth2,
        [publicKey]: {
          assets: {
            [ETH2_ASSET]: {
              amount: newAmount,
              usdValue: newValue,
            },
          },
        },
      },
    });

    const oldTotals = get(totals);
    const stakingTotals = oldTotals[Blockchain.ETH2];

    // In case the only tracked validators have exited and total is empty
    if (!stakingTotals[ETH2_ASSET])
      return;

    const { amount: oldTotalAmount, usdValue: oldTotalUsdValue } = stakingTotals[ETH2_ASSET];

    set(totals, {
      ...oldTotals,
      [Blockchain.ETH2]: {
        [ETH2_ASSET]: {
          amount: oldTotalAmount.plus(amountDiff),
          usdValue: oldTotalUsdValue.plus(valueDiff),
        },
      },
    });
  };

  return {
    balances,
    loopring,
    totals,
    liabilities,
    stakingBalances,
    update,
    updatePrices,
    getLoopringAssetBalances,
    fetchLoopringBalances,
    updateEthStakingOwnership,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useEthBalancesStore, import.meta.hot));
