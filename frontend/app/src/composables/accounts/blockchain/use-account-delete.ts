import type {
  BlockchainAccountBalance,
  EthereumValidator,
  XpubData,
} from '@/types/blockchain/accounts';
import { useBlockchainAccounts } from '@/composables/blockchain/accounts';
import { useEthStaking } from '@/composables/blockchain/accounts/staking';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainStore } from '@/store/blockchain';
import { useConfirmStore } from '@/store/confirm';
import { isBlockchain } from '@/types/blockchain/chains';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { Blockchain } from '@rotki/common';

type ShowConfirmationParams = {
  type: 'account';
  data: BlockchainAccountBalance;
} | {
  type: 'validator';
  data: EthereumValidator;
};

interface EvmPayloadData {
  address: string;
  chains: string[];
  includeAllChains: boolean;
};

type Payload = {
  type: 'validator';
  data: string;
} | {
  type: 'evm';
  data: EvmPayloadData;
} | {
  type: 'xpub';
  data: XpubData & { chain: string };
} | {
  type: 'account';
  data: {
    chain: string;
    address: string;
  };
};

function toPayload(params: ShowConfirmationParams): Payload {
  if (params.type === 'validator') {
    return {
      data: params.data.publicKey,
      type: 'validator',
    };
  }

  const account = params.data;
  const address = getAccountAddress(account);

  if (account.type === 'group') {
    if (account.data.type === 'xpub') {
      return {
        data: {
          ...account.data,
          chain: account.chains[0],
        },
        type: 'xpub',
      };
    }

    const { allChains, chains } = account;

    // Only allow Blockchain values, used to filter out virtual chains such as Loopring.
    const allFilteredChains = allChains?.filter(isBlockchain);
    const filteredChains = chains.filter(isBlockchain);

    // A group but only has 1 chain
    if (filteredChains.length === 1) {
      return {
        data: {
          address,
          chain: filteredChains[0],
        },
        type: 'account',
      };
    }

    // A group that showing multiple chains, but not all
    if (allFilteredChains && allFilteredChains.length > filteredChains.length) {
      return {
        data: {
          address,
          chains: filteredChains,
          includeAllChains: false,
        },
        type: 'evm',
      };
    }

    // A group that showing all its chains
    return {
      data: {
        address,
        chains: filteredChains,
        includeAllChains: true,
      },
      type: 'evm',
    };
  }

  // Single account inside the group
  return {
    data: {
      address,
      chain: account.chain,
    },
    type: 'account',
  };
}

interface UseAccountDeleteReturn {
  showConfirmation: (params: ShowConfirmationParams, onComplete?: () => void) => void;
}

export function useAccountDelete(): UseAccountDeleteReturn {
  const { deleteEth2Validators } = useEthStaking();
  const { deleteXpub, removeAccount, removeAgnosticAccount } = useBlockchainAccounts();
  const { removeAccounts } = useBlockchainStore();
  const { t } = useI18n();
  const { show } = useConfirmStore();
  const { getChainName } = useSupportedChains();

  async function removeValidator(publicKey: string): Promise<void> {
    await deleteEth2Validators([publicKey]);
    removeAccounts({ addresses: [publicKey], chains: [Blockchain.ETH2] });
  }

  async function removeGroupAccounts(
    category: string,
    { address, chains, includeAllChains }: EvmPayloadData,
  ): Promise<void> {
    if (includeAllChains) {
      await removeAgnosticAccount(category, address);
      removeAccounts({ addresses: [address], chains });
    }
    else {
      await awaitParallelExecution(
        chains,
        chain => chain,
        async chain => removeAccount({ accounts: [address], chain }),
        1,
      );

      removeAccounts({
        addresses: [address],
        chains,
      });
    }
  }

  async function removeSingleAccount({ address, chain }: { address: string; chain: string }): Promise<void> {
    await removeAccount({
      accounts: [address],
      chain,
    });

    removeAccounts({
      addresses: [address],
      chains: [chain],
    });
  }

  async function removeXpub(payload: XpubData & { chain: string }): Promise<void> {
    await deleteXpub(payload);
    removeAccounts({
      addresses: [getAccountAddress({ data: payload })],
      chains: [payload.chain],
    });
  }

  function getConfirmationMessage(params: ShowConfirmationParams): string {
    const address = params.type === 'validator' ? params.data.publicKey : getAccountAddress(params.data);

    if (params.type === 'validator') {
      const { index, publicKey } = params.data;
      return t('account_balances.confirm_delete.description_validator', { index, publicKey });
    }

    const account = params.data;

    if (account.type === 'group') {
      if (account.data.type === 'xpub')
        return t('account_balances.confirm_delete.description_xpub', { address });

      const { allChains, chains } = account;

      // Only allow Blockchain values, used to filter out virtual chains such as Loopring.
      const allFilteredChains = allChains?.filter(isBlockchain);
      const filteredChains = chains.filter(isBlockchain);

      // A group but only has 1 chain
      if (filteredChains.length === 1)
        return t('account_balances.confirm_delete.description_address', { address, chain: get(getChainName(filteredChains[0])) });

      // A group that showing multiple chains, but not all
      if (allFilteredChains && allFilteredChains.length > filteredChains.length)
        return t('account_balances.confirm_delete.description_multiple_address', { address, chains: filteredChains.map(item => get(getChainName(item))).join(', '), length: filteredChains.length });

      // A group that showing all its chains
      return t('account_balances.confirm_delete.agnostic.description', { address });
    }

    // Single account inside the group
    return t('account_balances.confirm_delete.description_address', { address, chain: get(getChainName(account.chain)) });
  }

  function showConfirmation(params: ShowConfirmationParams, onComplete?: () => void): void {
    const message = getConfirmationMessage(params);
    show({ message, title: t('account_balances.confirm_delete.title') }, async () => {
      const payload = toPayload(params);

      if (payload.type === 'account')
        await removeSingleAccount(payload.data);
      else if (payload.type === 'validator')
        await removeValidator(payload.data);
      else if (payload.type === 'xpub')
        await removeXpub(payload.data);
      else if (payload.type === 'evm')
        await removeGroupAccounts(payload.type, payload.data);

      onComplete?.();
    });
  }

  return {
    showConfirmation,
  };
}
