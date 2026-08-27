import type { Ref } from 'vue';
import { type MaybePromise, NotificationGroup } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useInjectedWallet } from '@/modules/wallet/bridge/use-injected-wallet';
import { isUserRejectedError, WALLET_MODES } from '@/modules/wallet/constants';
import { useWalletConnect } from '@/modules/wallet/use-wallet-connect';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
import { getAddress, type ViemWalletClient } from '@/modules/wallet/viem-client';
import { GnosisPayError, type GnosisPayErrorContext } from './types';
import { useGnosisPaySiweApi } from './use-gnosis-pay-api';

/**
 * EIP-4361 line 1 takes an authority (host, optionally with a port), not a URL. Only `URI:` takes a
 * scheme. Wallets compare this string against the requesting origin's host verbatim, so a `https://`
 * prefix here can never match any origin.
 */
const SIWE_DOMAIN = 'rotki.com';

const SIWE_URI = 'https://rotki.com';

interface UseGnosisPaySigningOptions {
  /** Clears the shared error state before signing, skipped when the pending error is `INVALID_ADDRESS` so that warning stays visible. */
  clearError: () => void;
  /** Comes from the wallet store via `useGnosisPayWallet`. Undefined means no wallet is connected and sign-in aborts immediately. */
  connectedAddress: Ref<string | undefined>;
  /** Read, never written: detects only the `INVALID_ADDRESS` warning, which must survive a sign-in attempt. */
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
  const { removeMatching, showErrorMessage } = useNotifications();
  const { submitTask } = useNativeTask();
  const { fetchNonce, verifySiweSignature } = useGnosisPaySiweApi();

  const { walletMode } = storeToRefs(useWalletStore());
  const injectedWallet = useInjectedWallet();
  const walletConnect = useWalletConnect();

  function createSiweMessage(address: string, nonce: string): string {
    const issuedAt = new Date().toISOString();

    return `${SIWE_DOMAIN} wants you to sign in with your Ethereum account:
${address}

Sign in with Ethereum to authenticate with Gnosis Pay.

URI: ${SIWE_URI}
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
   * Drops the session-expired warning once the backend has accepted the signature. Nothing else in
   * this flow writes to that group - progress goes to the task centre and failures to the message
   * dialog - so the warning is never superseded the way a grouped notification would be, and would
   * otherwise sit in the list still offering to re-authenticate a session that is now valid.
   */
  function clearSessionExpiredWarning(): void {
    removeMatching(({ group }) => group === NotificationGroup.GNOSIS_PAY_SESSION_EXPIRED);
  }

  /**
   * Reports a failed sign-in step. A non-actionable failure (a cancelled or superseded task) is
   * silent, since there is nothing for the user to act on.
   */
  function reportSignInFailure(error: TaskError): void {
    if (isActionable(error)) {
      showErrorMessage(t('external_services.gnosispay.siwe.failed'), error.message);
      logger.error('Sign-in with Ethereum failed:', error.message);
    }
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

      const nonceOutcome = await submitTask<string>({
        id: makeActivityId(ActivityKind.GNOSIS_PAY, ActivityPart.NONCE),
        kind: ActivityKind.GNOSIS_PAY,
        rerunnable: false,
        run: async ({ runTask }): Promise<Result<string, TaskError>> => mapResult(
          await runTask<string>(
            async () => fetchNonce(),
          ),
          value => value,
        ),
        subtitle: activityLabel(ActivityKind.GNOSIS_PAY, ActivityPart.NONCE),
        title: t('task_center.group.gnosis_pay'),
      });

      if (isErr(nonceOutcome)) {
        reportSignInFailure(nonceOutcome.error);
        return;
      }

      const message = createSiweMessage(address, nonceOutcome.value);
      const client = getWalletClient();
      const signature = await signMessage(client, address, message);

      const verifyOutcome = await submitTask<boolean>({
        id: makeActivityId(ActivityKind.GNOSIS_PAY, ActivityPart.VERIFY),
        kind: ActivityKind.GNOSIS_PAY,
        rerunnable: false,
        run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
          await runTask<boolean>(
            async () => verifySiweSignature(message, signature),
          ),
          value => value,
        ),
        subtitle: activityLabel(ActivityKind.GNOSIS_PAY, ActivityPart.VERIFY),
        title: t('task_center.group.gnosis_pay'),
      });

      if (isErr(verifyOutcome)) {
        reportSignInFailure(verifyOutcome.error);
        return;
      }

      if (verifyOutcome.value) {
        set(signInSuccess, true);
        clearSessionExpiredWarning();
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
