import type { MaybePromise } from '@rotki/common';
import type { Ref } from 'vue';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, type TaskFailure, type TaskResult, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useInjectedWallet } from '@/modules/wallet/bridge/use-injected-wallet';
import { isUserRejectedError, WALLET_MODES } from '@/modules/wallet/constants';
import { useWalletConnect } from '@/modules/wallet/use-wallet-connect';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
import { getAddress, type ViemWalletClient } from '@/modules/wallet/viem-client';
import { GnosisPayError, type GnosisPayErrorContext } from './types';
import { useGnosisPaySiweApi } from './use-gnosis-pay-api';

interface UseGnosisPaySigningOptions {
  /** Clears the shared error state before signing, skipped when the pending error is `INVALID_ADDRESS` so that warning stays visible. */
  clearError: () => void;
  /** Comes from the wallet store via `useGnosisPayWallet`. Undefined means no wallet is connected and sign-in aborts immediately. */
  connectedAddress: Ref<string | undefined>;
  /** Read, never written. Only used to detect the `INVALID_ADDRESS` warning that must be preserved across a sign-in attempt. */
  errorType: Ref<GnosisPayError | null>;
  /** Awaited once the backend confirms the signature. The auth card uses it to reload the API key and re-check the safe migration. */
  onSignInComplete?: () => MaybePromise<void>;
  /** Used only for the two locally recoverable cases (no wallet connected, user rejected the signature). Task failures go to notifications instead. */
  setError: (type: GnosisPayError, context?: GnosisPayErrorContext) => void;
  /** Held true across the whole nonce, sign, verify sequence and cleared in `finally`. The component also clears it to cancel. */
  signingInProgress: Ref<boolean>;
  /** Reset to false when sign-in starts, set to true only after backend verification. Advances the auth flow to its final step. */
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

  async function signMessage(client: ViemWalletClient, account: string, message: string): Promise<string> {
    return client.signMessage({ account: getAddress(account), message });
  }

  function getWalletClient(): ViemWalletClient {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE)
      return injectedWallet.getWalletClient();

    return walletConnect.getWalletClient();
  }

  /**
   * Reports a failed sign-in step and tells the caller to stop. A non-actionable failure (a cancelled
   * or superseded task) stops the flow silently, since there is nothing for the user to act on.
   */
  function reportSignInFailure<T>(outcome: TaskResult<T>): outcome is TaskFailure {
    if (outcome.success)
      return false;

    if (isActionableFailure(outcome)) {
      showErrorMessage(t('external_services.gnosispay.siwe.failed'), outcome.message);
      logger.error('Sign-in with Ethereum failed:', outcome.message);
    }

    return true;
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

      if (reportSignInFailure(nonceOutcome))
        return;

      const message = createSiweMessage(address, nonceOutcome.result);
      const client = getWalletClient();
      const signature = await signMessage(client, address, message);

      // Verify signature with async task
      const verifyOutcome = await runTask<boolean, TaskMeta>(
        async () => verifySiweSignature(message, signature),
        { type: TaskType.GNOSISPAY_VERIFY_SIGNATURE, meta: { title: t('external_services.gnosispay.siwe.verifying_signature') } },
      );

      if (reportSignInFailure(verifyOutcome))
        return;

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
