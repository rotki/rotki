import type { MaybePromise } from '@rotki/common';
import type { Ref } from 'vue';
import { err, flatMap, isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';
import { activityLabelOf } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useInjectedWallet } from '@/modules/wallet/bridge/use-injected-wallet';
import { isUserRejectedError, WALLET_MODES } from '@/modules/wallet/constants';
import { useWalletConnect } from '@/modules/wallet/use-wallet-connect';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
import { getAddress, type ViemWalletClient } from '@/modules/wallet/viem-client';
import { gnosisPayNonceActivity, gnosisPayVerifyActivity } from './gnosis-pay.activity';
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
  const { showErrorMessage } = useNotifications();
  const { submitTask } = useNativeTask();
  const { fetchNonce, verifySiweSignature } = useGnosisPaySiweApi();
  const { clear } = useRaisedConditionsStore();

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
   * Takes down the expired-session row once the backend has accepted the signature.
   *
   * @remarks
   * A verified sign-in is the only evidence the session is valid again: no route reports a session's
   * state, so without this the row would keep offering to re-authenticate a session that works.
   */
  function clearSessionExpiredCondition(): void {
    clear(({ kind }) => kind === RaisedConditionKind.GNOSIS_PAY_SESSION);
  }

  /**
   * Logs a failed sign-in step. The step's row in the task centre is what reports it to the user,
   * and a non-actionable failure (a cancelled or superseded task) is not logged either.
   */
  function reportSignInFailure(error: TaskError): void {
    if (isActionable(error))
      logger.error('Sign-in with Ethereum failed:', error.message);
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
        id: gnosisPayNonceActivity.id(),
        kind: gnosisPayNonceActivity.kind,
        rerunnable: false,
        run: async ({ runTask }): Promise<Result<string, TaskError>> => mapResult(
          await runTask<string>(
            async () => fetchNonce(),
          ),
          value => value,
        ),
        subtitle: activityLabelOf(gnosisPayNonceActivity),
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
        id: gnosisPayVerifyActivity.id(),
        kind: gnosisPayVerifyActivity.kind,
        rerunnable: false,
        run: async ({ runTask }): Promise<Result<boolean, TaskError>> => flatMap(
          await runTask<boolean>(
            async () => verifySiweSignature(message, signature),
          ),
          verified => verified ? ok(true) : err(TaskFailed({ message: t('external_services.gnosispay.siwe.failed') })),
        ),
        subtitle: activityLabelOf(gnosisPayVerifyActivity),
        title: t('task_center.group.gnosis_pay'),
      });

      if (isErr(verifyOutcome)) {
        reportSignInFailure(verifyOutcome.error);
        return;
      }

      set(signInSuccess, true);
      clearSessionExpiredCondition();
      if (onSignInComplete)
        await onSignInComplete();
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
