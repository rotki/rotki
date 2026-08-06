import type { AccountPayload, BlockchainAccount, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import { convertBtcAccounts } from '@/modules/accounts/account-helpers';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { createAccount } from '@/modules/accounts/create-account';
import { isBtcChain } from '@/modules/core/common/chains';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseAccountEditsReturn {
  editAccount: (payload: AccountPayload | XpubAccountPayload, chain: string) => Promise<BlockchainAccount[]>;
  editAgnosticAccount: (chainType: string, payload: AccountPayload) => Promise<boolean>;
}

export function useAccountEdits(): UseAccountEditsReturn {
  const { editAgnosticBlockchainAccount, editBlockchainAccount, editBtcAccount } = useBlockchainAccountsApi();
  const { resetAddressNamesData } = useAddressNameResolution();
  const { getNativeAsset } = useSupportedChains();

  /**
   * An edit can change a label, so any cached name for the address is stale. Failing to reset it is
   * cosmetic, never fatal, which is why this swallows rather than propagates.
   */
  const resetAddressesData = (chain: string | null, payload: AccountPayload): void => {
    try {
      resetAddressNamesData([{ address: payload.address, blockchain: chain }]);
    }
    catch (error: unknown) {
      logger.error(error);
    }
  };

  const editAccount = async (
    payload: AccountPayload | XpubAccountPayload,
    chain: string,
  ): Promise<BlockchainAccount[]> => {
    if (isBtcChain(chain) || 'xpub' in payload) {
      const response = convertBtcAccounts(getNativeAsset, chain, await editBtcAccount(payload, chain));

      if (!('xpub' in payload))
        resetAddressesData(chain, payload);

      return response;
    }

    const result = await editBlockchainAccount(payload, chain);

    resetAddressesData(chain, payload);

    const chainInfo = {
      chain,
      nativeAsset: getNativeAsset(chain),
    };

    return result.map(account => createAccount(account, chainInfo));
  };

  const editAgnosticAccount = async (chainType: string, payload: AccountPayload): Promise<boolean> => {
    const result = await editAgnosticBlockchainAccount(chainType, payload);
    resetAddressesData(null, payload);
    return result;
  };

  return { editAccount, editAgnosticAccount };
}
