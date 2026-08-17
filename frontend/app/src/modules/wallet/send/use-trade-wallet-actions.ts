import type { Ref } from 'vue';
import type { EnhancedProviderDetail } from '@/modules/wallet/providers/provider-detection';
import type { TransactionParams } from '@/modules/wallet/types';
import { logger } from '@/modules/core/common/logging/logging';
import { getWalletErrorMessage, isUserRejectedError } from '@/modules/wallet/constants';
import { useProviderSelection } from '@/modules/wallet/providers/use-provider-selection';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

interface UseTradeWalletActionsReturn {
  readonly errorMessage: Readonly<Ref<string>>;
  readonly clearError: () => void;
  readonly connect: () => Promise<void>;
  readonly disconnect: () => Promise<void>;
  readonly toggleConnection: () => Promise<void>;
  readonly send: (params: TransactionParams) => Promise<boolean>;
  readonly selectProvider: (provider: EnhancedProviderDetail) => Promise<void>;
}

/**
 * The wallet operations a send can trigger, each funnelling its failure into one message the card
 * shows. A user-rejected transaction is reported as a rejection rather than as a wallet error,
 * since it is a choice and not a fault.
 */
export function useTradeWalletActions(): UseTradeWalletActionsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const errorMessage = shallowRef<string>('');

  function clearError(): void {
    set(errorMessage, '');
  }

  const walletStore = useWalletStore();
  const { connected } = storeToRefs(walletStore);
  const { connect: connectWallet, disconnect: disconnectWallet, sendTransaction } = walletStore;
  const { handleProviderSelection } = useProviderSelection();

  /** Runs a wallet call, reporting any failure through {@link errorMessage}. */
  async function guarded(action: () => Promise<void>): Promise<boolean> {
    try {
      clearError();
      await action();
      return true;
    }
    catch (error: unknown) {
      logger.error(error);
      set(errorMessage, getWalletErrorMessage(error));
      return false;
    }
  }

  async function connect(): Promise<void> {
    await guarded(async () => {
      await connectWallet();
    });
  }

  async function disconnect(): Promise<void> {
    await guarded(async () => {
      await disconnectWallet();
    });
  }

  async function toggleConnection(): Promise<void> {
    if (get(connected))
      await disconnect();
    else
      await connect();
  }

  /** Resolves to whether the transaction was accepted, so the caller can clear the form. */
  async function send(params: TransactionParams): Promise<boolean> {
    try {
      clearError();
      await sendTransaction(params);
      return true;
    }
    catch (error: unknown) {
      set(errorMessage, isUserRejectedError(error) ? t('trade.errors.rejected') : getWalletErrorMessage(error));
      return false;
    }
  }

  async function selectProvider(provider: EnhancedProviderDetail): Promise<void> {
    await handleProviderSelection(provider, (message) => {
      set(errorMessage, message);
    });
  }

  return {
    clearError,
    connect,
    disconnect,
    errorMessage: readonly(errorMessage),
    selectProvider,
    send,
    toggleConnection,
  };
}
