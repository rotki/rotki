import type { MaybePromise } from '@rotki/common';
import type { BrowserProvider } from 'ethers';
import type { Ref } from 'vue';
import type { TaskMeta } from '@/types/task';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useInjectedWallet } from '@/modules/onchain/wallet-bridge/use-injected-wallet';
import { useWalletConnect } from '@/modules/onchain/wallet-connect/use-wallet-connect';
import { isUserRejectedError, WALLET_MODES } from '@/modules/onchain/wallet-constants';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { logger } from '@/utils/logging';
import { GnosisPayError, type GnosisPayErrorContext } from './types';
import { useGnosisPaySiweApi } from './use-gnosis-pay-api';

interface UseGnosisPaySigningOptions {
  clearError: () => void;
  connectedAddress: Ref<string | undefined>;
  errorType: Ref<GnosisPayError | null>;
  onSignInComplete?: () => MaybePromise<void>;
  setError: (type: GnosisPayError, context?: GnosisPayErrorContext) => void;
  signingInProgress: Ref<boolean>;
  signInSuccess: Ref<boolean>;
}

interface UseGnosisPaySigningReturn {
  signInWithEthereum: () => Promise<void>;
}

/**
 * Composable for managing SIWE (Sign-In with Ethereum) signing flow
 */
export function useGnosisPaySigning(options: UseGnosisPaySigningOptions): UseGnosisPaySigningReturn {
  const {
    clearError,
    connectedAddress,
    errorType,
    onSignInComplete,
    setError,
    signingInProgress,
    signInSuccess,
  } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { setMessage } = useMessageStore();
  const { awaitTask } = useTaskStore();
  const { fetchNonce, verifySiweSignature } = useGnosisPaySiweApi();

  const { walletMode } = storeToRefs(useWalletStore());
  const injectedWallet = useInjectedWallet();
  const walletConnect = useWalletConnect();

  function createSiweMessage(address: string, nonce: string): string {
    const domain = 'https://rotki.com';
    const issuedAt = new Date().toISOString();

    return `${domain} wants you to sign in with your Ethereum account:
${address}

Sign in with Ethereum to authenticate with Gnosis Pay.

URI: ${domain}
Version: 1
Chain ID: 100
Nonce: ${nonce}
Issued At: ${issuedAt}`;
  }

  async function signMessage(provider: BrowserProvider, message: string): Promise<string> {
    const signer = await provider.getSigner();
    return signer.signMessage(message);
  }

  function getBrowserProvider(): BrowserProvider {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE)
      return injectedWallet.getBrowserProvider();

    return walletConnect.getBrowserProvider();
  }

  async function signInWithEthereum(): Promise<void> {
    try {
      // Preserve INVALID_ADDRESS warning during sign-in
      if (get(errorType) !== GnosisPayError.INVALID_ADDRESS)
        clearError();

      set(signingInProgress, true);
      set(signInSuccess, false);

      const address = get(connectedAddress);
      if (!address) {
        setError(GnosisPayError.NO_WALLET_CONNECTED);
        return;
      }

      // Fetch nonce with async task
      const nonceTask = await fetchNonce();
      const { result: nonce } = await awaitTask<string, TaskMeta>(
        nonceTask.taskId,
        TaskType.GNOSISPAY_FETCH_NONCE,
        {
          title: t('external_services.gnosispay.siwe.fetching_nonce'),
        },
      );

      const message = createSiweMessage(address, nonce);
      const provider = getBrowserProvider();
      const signature = await signMessage(provider, message);

      // Verify signature with async task
      const verifyTask = await verifySiweSignature(message, signature);
      const { result } = await awaitTask<boolean, TaskMeta>(
        verifyTask.taskId,
        TaskType.GNOSISPAY_VERIFY_SIGNATURE,
        {
          title: t('external_services.gnosispay.siwe.verifying_signature'),
        },
      );

      if (result) {
        set(signInSuccess, true);
        if (onSignInComplete)
          await onSignInComplete();
      }
      else {
        throw new Error(t('external_services.gnosispay.siwe.failed'));
      }
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        if (isUserRejectedError(error)) {
          setError(GnosisPayError.SIGNATURE_REJECTED);
        }
        else {
          setMessage({
            description: error.toString(),
            success: false,
            title: t('external_services.gnosispay.siwe.failed'),
          });
        }
        logger.error('Sign-in with Ethereum failed:', error);
      }
    }
    finally {
      set(signingInProgress, false);
    }
  }

  return {
    signInWithEthereum,
  };
}
