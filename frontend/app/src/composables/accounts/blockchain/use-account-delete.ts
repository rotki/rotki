import { Blockchain } from '@rotki/common/lib/blockchain';
import type { Account } from '@rotki/common/lib/account';
import type {
  BlockchainAccountGroupWithBalance,
  BlockchainAccountWithBalance,
  DeleteXpubParams,
  XpubData,
} from '@/types/blockchain/accounts';

export function isGroupXpub(
  account: BlockchainAccountGroupWithBalance,
): account is BlockchainAccountGroupWithBalance<XpubData> {
  return 'xpub' in account.data;
}

type DataRow = BlockchainAccountWithBalance | BlockchainAccountGroupWithBalance;

export function useAccountDelete() {
  const { deleteEth2Validators } = useEthStaking();
  const { removeAccount, deleteXpub } = useBlockchainAccounts();
  const { refreshAccounts } = useBlockchains();
  const { t } = useI18n();
  const { show } = useConfirmStore();

  async function deleteAccount(payload: DataRow[]): Promise<void> {
    if (payload.length === 0)
      return;

    const validators: string[] = [];
    const chainAccounts: Account[] = [];
    const xpubs: DeleteXpubParams[] = [];

    payload.forEach((account) => {
      if ('publicKey' in account.data) {
        validators.push(account.data.publicKey);
      }
      else if ('xpub' in account.data) {
        const chain = getChain(account);
        assert(chain);
        xpubs.push({
          xpub: account.data.xpub,
          derivationPath: account.data.derivationPath,
          chain,
        });
      }
      else if ('address' in account.data) {
        if ('chain' in account) {
          if (!account.virtual) {
            chainAccounts.push({
              address: account.data.address,
              chain: account.chain,
            });
          }
        }
        else if ('chains' in account) {
          for (const chain of account.chains) {
            chainAccounts.push({
              address: account.data.address,
              chain,
            });
          }
        }
      }
    });

    const chainsToRefresh = [];
    if (validators.length > 0) {
      await deleteEth2Validators(validators);
      chainsToRefresh.push(Blockchain.ETH2);
    }

    if (chainAccounts.length > 0) {
      const deletion = chainAccounts.reduce((previousValue, currentValue) => {
        if (!previousValue[currentValue.chain])
          previousValue[currentValue.chain] = [currentValue.address];
        else
          previousValue[currentValue.chain].push(currentValue.address);
        return previousValue;
      }, {} as Record<string, string[]>);

      for (const [chain, accounts] of Object.entries(deletion)) {
        chainsToRefresh.push(chain);
        await removeAccount({
          accounts,
          chain,
        });
      }
    }

    if (xpubs.length > 0) {
      for (const xpub of xpubs) {
        chainsToRefresh.push(xpub.chain);
        await deleteXpub(xpub);
      }
    }

    chainsToRefresh.filter(uniqueStrings).forEach((chain) => {
      startPromise(refreshAccounts(chain));
    });
  }

  function showConfirmation(payload: DataRow[]) {
    const message: string = Array.isArray(payload)
      ? t('account_balances.confirm_delete.description_address', {
        count: payload.length,
      })
      : t('account_balances.confirm_delete.description_xpub', {
        address: payload,
      });
    show(
      {
        title: t('account_balances.confirm_delete.title'),
        message,
      },
      async () => {
        await deleteAccount(payload);
      },
    );
  }

  return {
    showConfirmation,
  };
}
