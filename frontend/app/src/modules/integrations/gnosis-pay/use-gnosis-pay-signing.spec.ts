import type { BrowserProvider } from 'ethers';
import type { Ref } from 'vue';
import type { TaskResult } from '@/modules/core/tasks/use-task-handler';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { GnosisPayError, type GnosisPayErrorContext } from './types';
import { useGnosisPaySigning } from './use-gnosis-pay-signing';

const fetchNonce = vi.fn();
const verifySiweSignature = vi.fn();
const runTask = vi.fn();
const showErrorMessage = vi.fn();
const signMessage = vi.fn();
const getSigner = vi.fn();
const injectedGetBrowserProvider = vi.fn();
const wcGetBrowserProvider = vi.fn();
const walletMode = ref<string>('local-bridge');

vi.mock('@/modules/integrations/gnosis-pay/use-gnosis-pay-api', () => ({
  useGnosisPaySiweApi: vi.fn().mockImplementation(() => ({
    fetchNonce,
    verifySiweSignature,
  })),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async () => {
  const actual = await vi.importActual<typeof import('@/modules/core/tasks/use-task-handler')>(
    '@/modules/core/tasks/use-task-handler',
  );
  return {
    ...actual,
    useTaskHandler: vi.fn().mockImplementation(() => ({ runTask })),
  };
});

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockImplementation(() => ({ showErrorMessage })),
}));

vi.mock('@/modules/wallet/bridge/use-injected-wallet', () => ({
  useInjectedWallet: vi.fn().mockImplementation(() => ({
    getBrowserProvider: injectedGetBrowserProvider,
  })),
}));

vi.mock('@/modules/wallet/use-wallet-connect', () => ({
  useWalletConnect: vi.fn().mockImplementation(() => ({
    getBrowserProvider: wcGetBrowserProvider,
  })),
}));

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: vi.fn().mockImplementation(() => ({ walletMode })),
}));

vi.mock('@/modules/wallet/constants', () => ({
  WALLET_MODES: { LOCAL_BRIDGE: 'local-bridge', WALLET_CONNECT: 'walletconnect' },
  isUserRejectedError: (error: unknown): boolean => String(error).includes('User rejected'),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

function makeSuccess<T>(result: T): TaskResult<T> {
  return { result, success: true };
}

function makeFailure(message: string, opts: Partial<{ cancelled: boolean; skipped: boolean }> = {}): TaskResult<never> {
  return {
    backendCancelled: false,
    cancelled: opts.cancelled ?? false,
    message,
    skipped: opts.skipped ?? false,
    success: false,
  };
}

interface Harness {
  clearError: Mock<() => void>;
  connectedAddress: Ref<string | undefined>;
  errorType: Ref<GnosisPayError | null>;
  onSignInComplete?: Mock<() => void | Promise<void>>;
  setError: Mock<(type: GnosisPayError, context?: GnosisPayErrorContext) => void>;
  signingInProgress: Ref<boolean>;
  signInSuccess: Ref<boolean>;
}

function makeHarness(overrides: Partial<Harness> = {}): Harness {
  return {
    clearError: vi.fn(),
    connectedAddress: ref<string | undefined>('0xConnected'),
    errorType: ref<GnosisPayError | null>(null),
    setError: vi.fn(),
    signingInProgress: ref<boolean>(false),
    signInSuccess: ref<boolean>(false),
    ...overrides,
  };
}

describe('useGnosisPaySigning', () => {
  beforeEach(() => {
    fetchNonce.mockReset();
    verifySiweSignature.mockReset();
    runTask.mockReset();
    showErrorMessage.mockReset();
    signMessage.mockReset().mockResolvedValue('0xSignature');
    getSigner.mockReset().mockResolvedValue({ signMessage });
    const fakeProvider: Pick<BrowserProvider, 'getSigner'> = { getSigner };
    injectedGetBrowserProvider.mockReset().mockReturnValue(fakeProvider);
    wcGetBrowserProvider.mockReset().mockReturnValue(fakeProvider);
    set(walletMode, 'local-bridge');
  });

  it('should clear error when starting a fresh sign-in', async () => {
    const harness = makeHarness();
    runTask.mockImplementation(async (fn: () => Promise<unknown>) => {
      await fn();
      return makeSuccess('nonce-1');
    });
    runTask.mockImplementationOnce(async () => makeSuccess('nonce-1'));
    runTask.mockImplementationOnce(async () => makeSuccess(true));

    const { signInWithEthereum } = useGnosisPaySigning({ ...harness, signInSuccess: harness.signInSuccess });
    await signInWithEthereum();

    expect(harness.clearError).toHaveBeenCalled();
  });

  it('should preserve INVALID_ADDRESS warning while signing', async () => {
    const harness = makeHarness({ errorType: ref(GnosisPayError.INVALID_ADDRESS) });
    runTask.mockImplementationOnce(async () => makeSuccess('nonce'));
    runTask.mockImplementationOnce(async () => makeSuccess(true));

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(harness.clearError).not.toHaveBeenCalled();
  });

  it('should set NO_WALLET_CONNECTED when no address is connected', async () => {
    const harness = makeHarness({ connectedAddress: ref<string | undefined>(undefined) });

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(harness.setError).toHaveBeenCalledWith(GnosisPayError.NO_WALLET_CONNECTED);
    expect(runTask).not.toHaveBeenCalled();
    expect(get(harness.signingInProgress)).toBe(false);
  });

  it('should sign in successfully and invoke onSignInComplete', async () => {
    const onSignInComplete = vi.fn();
    const harness = makeHarness();
    runTask.mockImplementationOnce(async () => makeSuccess('nonce-123'));
    runTask.mockImplementationOnce(async () => makeSuccess(true));

    const { signInWithEthereum } = useGnosisPaySigning({ ...harness, onSignInComplete });
    await signInWithEthereum();

    expect(fetchNonce).not.toHaveBeenCalled();
    expect(runTask).toHaveBeenCalledTimes(2);
    expect(signMessage).toHaveBeenCalledTimes(1);
    const signedMessage = String(signMessage.mock.calls[0][0]);
    expect(signedMessage).toContain('0xConnected');
    expect(signedMessage).toContain('Nonce: nonce-123');
    expect(get(harness.signInSuccess)).toBe(true);
    expect(onSignInComplete).toHaveBeenCalled();
    expect(get(harness.signingInProgress)).toBe(false);
  });

  it('should bail out when fetching the nonce fails actionably', async () => {
    const harness = makeHarness();
    runTask.mockImplementationOnce(async () => makeFailure('nonce error'));

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(showErrorMessage).toHaveBeenCalled();
    expect(signMessage).not.toHaveBeenCalled();
    expect(get(harness.signInSuccess)).toBe(false);
  });

  it('should not show error message when nonce fetch is cancelled', async () => {
    const harness = makeHarness();
    runTask.mockImplementationOnce(async () => makeFailure('cancelled', { cancelled: true }));

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(showErrorMessage).not.toHaveBeenCalled();
    expect(signMessage).not.toHaveBeenCalled();
  });

  it('should bail out when verification fails', async () => {
    const harness = makeHarness();
    runTask.mockImplementationOnce(async () => makeSuccess('nonce'));
    runTask.mockImplementationOnce(async () => makeFailure('verify failed'));

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(showErrorMessage).toHaveBeenCalled();
    expect(get(harness.signInSuccess)).toBe(false);
  });

  it('should show generic failure when verification returns false', async () => {
    const harness = makeHarness();
    runTask.mockImplementationOnce(async () => makeSuccess('nonce'));
    runTask.mockImplementationOnce(async () => makeSuccess(false));

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(showErrorMessage).toHaveBeenCalled();
    expect(get(harness.signInSuccess)).toBe(false);
  });

  it('should detect a user-rejected signature error', async () => {
    const harness = makeHarness();
    runTask.mockImplementationOnce(async () => makeSuccess('nonce'));
    signMessage.mockRejectedValueOnce(new Error('User rejected the request'));

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(harness.setError).toHaveBeenCalledWith(GnosisPayError.SIGNATURE_REJECTED);
    expect(showErrorMessage).not.toHaveBeenCalled();
  });

  it('should show a generic error when signing throws an unknown error', async () => {
    const harness = makeHarness();
    runTask.mockImplementationOnce(async () => makeSuccess('nonce'));
    signMessage.mockRejectedValueOnce(new Error('boom'));

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(harness.setError).not.toHaveBeenCalledWith(GnosisPayError.SIGNATURE_REJECTED);
    expect(showErrorMessage).toHaveBeenCalled();
  });

  it('should use the wallet-connect provider when in walletconnect mode', async () => {
    set(walletMode, 'walletconnect');
    const harness = makeHarness();
    runTask.mockImplementationOnce(async () => makeSuccess('nonce'));
    runTask.mockImplementationOnce(async () => makeSuccess(true));

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(wcGetBrowserProvider).toHaveBeenCalled();
    expect(injectedGetBrowserProvider).not.toHaveBeenCalled();
  });

  it('should always reset signingInProgress when finished', async () => {
    const harness = makeHarness();
    runTask.mockImplementationOnce(async () => {
      throw new Error('unexpected');
    });

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(get(harness.signingInProgress)).toBe(false);
  });

  it('should run the task helpers with the expected task types', async () => {
    const harness = makeHarness();
    runTask.mockImplementationOnce(async (fn: () => Promise<string>) => {
      await fn();
      return makeSuccess('nonce');
    });
    runTask.mockImplementationOnce(async (fn: () => Promise<boolean>) => {
      await fn();
      return makeSuccess(true);
    });

    const { signInWithEthereum } = useGnosisPaySigning(harness);
    await signInWithEthereum();

    expect(fetchNonce).toHaveBeenCalled();
    expect(verifySiweSignature).toHaveBeenCalled();
    const verifyArgs = verifySiweSignature.mock.calls[0];
    expect(verifyArgs[0]).toContain('0xConnected');
    expect(verifyArgs[1]).toBe('0xSignature');
  });
});
