import { Blockchain } from '@rotki/common';
import { type MaybeRef, objectPick } from '@vueuse/core';
import { Module } from '@/types/modules';
import type { EthereumValidator, EthereumValidatorRequestPayload } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';

export const useBlockchainValidatorsStore = defineStore('blockchain/validators', () => {
  const blockchainStore = useBlockchainStore();
  const { blockchainAccounts } = storeToRefs(blockchainStore);
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { updateAccounts } = blockchainStore;

  const { getEth2Validators } = useBlockchainAccountsApi();
  const { activeModules } = storeToRefs(useGeneralSettingsStore());

  const isEth2Enabled = (): boolean => get(activeModules).includes(Module.ETH2);
  const { getNativeAsset } = useSupportedChains();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const stakingValidatorsLimits = ref<{
    limit: number;
    total: number;
  }>();

  const ethStakingValidators = computed<EthereumValidator[]>(() => {
    const validatorAccounts = get(blockchainAccounts)[Blockchain.ETH2] ?? [];
    return validatorAccounts.filter(isAccountWithBalanceValidator).map(validator => ({
      ...objectPick(validator, ['value', 'amount']),
      ...validator.data,
    }));
  });

  const fetchValidators = async (
    payload: MaybeRef<EthereumValidatorRequestPayload>,
  ): Promise<Collection<EthereumValidator>> => new Promise(
    (resolve) => {
      resolve(sortAndFilterValidators(
        get(ethStakingValidators),
        get(payload),
      ));
    },
  );

  const fetchEthStakingValidators = async (): Promise<void> => {
    if (!isEth2Enabled())
      return;

    try {
      const validators = await getEth2Validators();
      updateAccounts(
        Blockchain.ETH2,
        validators.entries.map(validator =>
          createValidatorAccount(validator, {
            chain: Blockchain.ETH2,
            nativeAsset: getNativeAsset(Blockchain.ETH2),
          }),
        ),
      );
      set(stakingValidatorsLimits, { limit: validators.entriesLimit, total: validators.entriesFound });
    }
    catch (error: any) {
      logger.error(error);
      notify({
        title: t('actions.get_accounts.error.title'),
        message: t('actions.get_accounts.error.description', {
          blockchain: Blockchain.ETH2,
          message: error.message,
        }),
        display: true,
      });
    }
  };

  const premium = usePremium();

  watch(premium, async () => {
    if (isEth2Enabled()) {
      await fetchEthStakingValidators();
      await fetchBlockchainBalances({
        ignoreCache: true,
        blockchain: Blockchain.ETH2,
      });
    }
  });

  return {
    stakingValidatorsLimits,
    ethStakingValidators,
    fetchValidators,
    fetchEthStakingValidators,
  };
});
