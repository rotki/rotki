import { Blockchain } from '@rotki/common';
import type {
  BlockchainAccountBalance,
  EthereumValidator,
  XpubData,
} from '@/types/blockchain/accounts';

type ShowConfirmationParams = {
  type: 'account';
  data: BlockchainAccountBalance;
} | {
  type: 'validator';
  data: EthereumValidator;
};

type Payload = {
  type: 'validator';
  data: string;
} | {
  type: 'evm';
  data: {
    address: string;
    chains: string[];
  };
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
      type: 'validator',
      data: params.data.publicKey,
    };
  }

  const account = params.data;

  if (account.type === 'group') {
    if (account.category === 'evm') {
      return {
        type: 'evm',
        data: {
          address: getAccountAddress(account),
          chains: account.chains,
        },
      };
    }
    else if (account.data.type === 'xpub') {
      return {
        type: 'xpub',
        data: {
          ...account.data,
          chain: account.chains[0],
        },
      };
    }
    else {
      return {
        type: 'account',
        data: {
          chain: account.chains[0],
          address: getAccountAddress(account),
        },
      };
    }
  }

  return {
    type: 'account',
    data: {
      chain: account.chain,
      address: getAccountAddress(account),
    },
  };
}

interface UseAccountDeleteReturn {
  showConfirmation: (params: ShowConfirmationParams, onComplete?: () => void) => void;
}

export function useAccountDelete(): UseAccountDeleteReturn {
  const { deleteEth2Validators } = useEthStaking();
  const { removeAccount, removeAgnosticAccount, deleteXpub } = useBlockchainAccounts();
  const { removeAccounts } = useBlockchainStore();
  const { t } = useI18n();
  const { show } = useConfirmStore();

  async function removeValidator(publicKey: string): Promise<void> {
    await deleteEth2Validators([publicKey]);
    removeAccounts({ addresses: [publicKey], chains: [Blockchain.ETH2] });
  }

  async function removeGroupAccounts(
    category: string,
    { address, chains }: { address: string; chains: string[] },
  ): Promise<void> {
    await removeAgnosticAccount(category, address);
    removeAccounts({ addresses: [address], chains });
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

  function showConfirmation(params: ShowConfirmationParams, onComplete?: () => void): void {
    const address = params.type === 'validator' ? params.data.publicKey : getAccountAddress(params.data);

    let message: string = t('account_balances.confirm_delete.description_address', { address });
    if (params.type === 'account') {
      if (params.data.data.type === 'xpub')
        message = t('account_balances.confirm_delete.description_xpub', { address });
      else if (params.data.category)
        message = t('account_balances.confirm_delete.agnostic.description', { address });
    }

    show({ title: t('account_balances.confirm_delete.title'), message }, async () => {
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
