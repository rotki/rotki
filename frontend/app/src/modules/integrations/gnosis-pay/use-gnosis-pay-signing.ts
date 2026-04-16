import type { MaybePromise } from '@rotki/common';
import type { BrowserProvider } from 'ethers';
import type { Ref } from 'vue';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useInjectedWallet } from '@/modules/wallet/bridge/use-injected-wallet';
import { isUserRejectedError, WALLET_MODES } from '@/modules/wallet/constants';
import { useWalletConnect } from '@/modules/wallet/use-wallet-connect';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
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
  const { showErrorMessage } = useNotifications();
  const { runTask } = useTaskHandler();
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
      const nonceOutcome = await runTask<string, TaskMeta>(
        async () => fetchNonce(),
        { type: TaskType.GNOSISPAY_FETCH_NONCE, meta: { title: t('external_services.gnosispay.siwe.fetching_nonce') } },
      );

      if (!nonceOutcome.success) {
        if (isActionableFailure(nonceOutcome)) {
          showErrorMessage(t('external_services.gnosispay.siwe.failed'), nonceOutcome.message);
          logger.error('Sign-in with Ethereum failed:', nonceOutcome.message);
        }
        return;
      }

      const message = createSiweMessage(address, nonceOutcome.result);
      const provider = getBrowserProvider();
      const signature = await signMessage(provider, message);

      // Verify signature with async task
      const verifyOutcome = await runTask<boolean, TaskMeta>(
        async () => verifySiweSignature(message, signature),
        { type: TaskType.GNOSISPAY_VERIFY_SIGNATURE, meta: { title: t('external_services.gnosispay.siwe.verifying_signature') } },
      );

      if (!verifyOutcome.success) {
        if (isActionableFailure(verifyOutcome)) {
          showErrorMessage(t('external_services.gnosispay.siwe.failed'), verifyOutcome.message);
          logger.error('Sign-in with Ethereum failed:', verifyOutcome.message);
        }
        return;
      }

      if (verifyOutcome.result) {
        set(signInSuccess, true);
        if (onSignInComplete)
          await onSignInComplete();
      }
      else {
        showErrorMessage(t('external_services.gnosispay.siwe.failed'), t('external_services.gnosispay.siwe.failed'));
        logger.error('Sign-in with Ethereum failed: verification returned false');
      }
    }
    catch (error: unknown) {
      if (isUserRejectedError(error)) {
        setError(GnosisPayError.SIGNATURE_REJECTED);
      }
      else {
        showErrorMessage(t('external_services.gnosispay.siwe.failed'), String(error));
      }
      logger.error('Sign-in with Ethereum failed:', error);
    }
    finally {
      set(signingInProgress, false);
    }
  }

  return {
    signInWithEthereum,
  };
}
