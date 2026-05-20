import type { Ref } from 'vue';
import type { EnhancedProviderDetail } from '@/modules/wallet/providers/provider-detection';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { type GnosisPayAdminsMapping, GnosisPayError } from './types';
import { useGnosisPayWallet } from './use-gnosis-pay-wallet';

const fetchGnosisPayAdmins = vi.fn();
const connectWallet = vi.fn();
const disconnectWallet = vi.fn();
const handleProviderSelectionBase = vi.fn();
const connected = ref<boolean>(false);
const connectedAddress = ref<string | undefined>();

vi.mock('@/modules/integrations/gnosis-pay/use-gnosis-pay-api', () => ({
  useGnosisPaySiweApi: vi.fn().mockImplementation(() => ({
    fetchGnosisPayAdmins,
  })),
}));

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: vi.fn().mockImplementation(() => ({
    connect: connectWallet,
    connected,
    connectedAddress,
    disconnect: disconnectWallet,
  })),
}));

vi.mock('@/modules/wallet/providers/use-provider-selection', () => ({
  useProviderSelection: vi.fn().mockImplementation(() => ({
    handleProviderSelection: handleProviderSelectionBase,
  })),
}));

vi.mock('@/modules/core/common/logging/error-handling', () => ({
  getErrorMessage: vi.fn().mockImplementation(err => (err instanceof Error ? err.message : String(err))),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

interface Options {
  checkingRegisteredAccounts: Ref<boolean>;
  clearError: Mock<() => void>;
  clearValidation: Mock<() => void>;
  controlledSafeAddresses: Ref<string[]>;
  gnosisPayAdminsMapping: Ref<GnosisPayAdminsMapping>;
  hasRegisteredAccounts: Ref<boolean>;
  isAddressValid: Ref<boolean>;
  setError: Mock<(type: GnosisPayError, context?: { adminsMapping?: GnosisPayAdminsMapping; message?: string }) => void>;
  validatingAddress: Ref<boolean>;
}

function makeOptions(overrides: Partial<Options> = {}): Options {
  return {
    checkingRegisteredAccounts: ref<boolean>(false),
    clearError: vi.fn(),
    clearValidation: vi.fn(),
    controlledSafeAddresses: ref<string[]>([]),
    gnosisPayAdminsMapping: ref<GnosisPayAdminsMapping>({}),
    hasRegisteredAccounts: ref<boolean>(false),
    isAddressValid: ref<boolean>(false),
    setError: vi.fn(),
    validatingAddress: ref<boolean>(false),
    ...overrides,
  };
}

describe('useGnosisPayWallet', () => {
  beforeEach(() => {
    fetchGnosisPayAdmins.mockReset();
    connectWallet.mockReset().mockResolvedValue(undefined);
    disconnectWallet.mockReset().mockResolvedValue(undefined);
    handleProviderSelectionBase.mockReset().mockResolvedValue(undefined);
    set(connected, false);
    set(connectedAddress, undefined);
  });

  describe('isWalletConnected', () => {
    it('should require both connected flag and a connected address', () => {
      const { isWalletConnected } = useGnosisPayWallet(makeOptions());
      expect(get(isWalletConnected)).toBe(false);

      set(connected, true);
      expect(get(isWalletConnected)).toBe(false);

      set(connectedAddress, '0xAbc');
      expect(get(isWalletConnected)).toBe(true);

      set(connected, false);
      expect(get(isWalletConnected)).toBe(false);
    });
  });

  describe('checkRegisteredAccounts', () => {
    it('should set NO_REGISTERED_ACCOUNTS error when admin mapping is empty', async () => {
      fetchGnosisPayAdmins.mockResolvedValue({});
      const options = makeOptions();

      const { checkRegisteredAccounts } = useGnosisPayWallet(options);
      await checkRegisteredAccounts();

      expect(options.clearError).toHaveBeenCalled();
      expect(options.setError).toHaveBeenCalledWith(GnosisPayError.NO_REGISTERED_ACCOUNTS);
      expect(get(options.hasRegisteredAccounts)).toBe(false);
      expect(get(options.checkingRegisteredAccounts)).toBe(false);
    });

    it('should populate adminsMapping when accounts are returned', async () => {
      const mapping: GnosisPayAdminsMapping = { '0xSafe1': ['0xAdmin1', '0xAdmin2'] };
      fetchGnosisPayAdmins.mockResolvedValue(mapping);
      const options = makeOptions();

      const { checkRegisteredAccounts } = useGnosisPayWallet(options);
      await checkRegisteredAccounts();

      expect(options.setError).not.toHaveBeenCalled();
      expect(get(options.hasRegisteredAccounts)).toBe(true);
      expect(get(options.gnosisPayAdminsMapping)).toEqual(mapping);
    });

    it('should map api errors to GnosisPayError.OTHER', async () => {
      fetchGnosisPayAdmins.mockRejectedValue(new Error('network down'));
      const options = makeOptions();

      const { checkRegisteredAccounts } = useGnosisPayWallet(options);
      await checkRegisteredAccounts();

      expect(options.setError).toHaveBeenCalledWith(GnosisPayError.OTHER, { message: 'network down' });
      expect(get(options.hasRegisteredAccounts)).toBe(false);
      expect(get(options.checkingRegisteredAccounts)).toBe(false);
    });
  });

  describe('handleProviderSelection', () => {
    it('should forward provider to base and pass a CONNECTION_FAILED error callback', async () => {
      const options = makeOptions();
      const provider: EnhancedProviderDetail = {
        info: { icon: '', name: 'Test Wallet', rdns: 'test.wallet', uuid: 'wallet-1' },
        provider: { request: vi.fn() },
        source: 'eip6963',
      };

      const { handleProviderSelection } = useGnosisPayWallet(options);
      await handleProviderSelection(provider);

      expect(handleProviderSelectionBase).toHaveBeenCalledTimes(1);
      const [calledProvider, onError] = handleProviderSelectionBase.mock.calls[0];
      expect(calledProvider).toBe(provider);

      onError('connection refused');
      expect(options.setError).toHaveBeenCalledWith(
        GnosisPayError.CONNECTION_FAILED,
        { message: 'connection refused' },
      );
    });
  });

  describe('validateAddress', () => {
    it('should set NO_WALLET_CONNECTED when no address is connected', async () => {
      const options = makeOptions();

      const { validateAddress } = useGnosisPayWallet(options);
      await validateAddress();

      expect(options.setError).toHaveBeenCalledWith(GnosisPayError.NO_WALLET_CONNECTED);
      expect(get(options.isAddressValid)).toBe(false);
    });

    it('should set INVALID_ADDRESS when the connected address controls no safe', async () => {
      const adminsMapping: GnosisPayAdminsMapping = { '0xSafe': ['0xOther'] };
      const options = makeOptions({
        gnosisPayAdminsMapping: ref<GnosisPayAdminsMapping>(adminsMapping),
      });
      set(connectedAddress, '0xConnected');

      const { validateAddress } = useGnosisPayWallet(options);
      await validateAddress();

      expect(options.setError).toHaveBeenCalledWith(
        GnosisPayError.INVALID_ADDRESS,
        { adminsMapping },
      );
      expect(get(options.isAddressValid)).toBe(false);
    });

    it('should mark address valid and populate controlled safes (case-insensitive)', async () => {
      const adminsMapping: GnosisPayAdminsMapping = {
        '0xSafeA': ['0xMINE'],
        '0xSafeB': ['0xother'],
        '0xSafeC': ['0xmine', '0xanother'],
      };
      const options = makeOptions({
        gnosisPayAdminsMapping: ref<GnosisPayAdminsMapping>(adminsMapping),
      });
      set(connectedAddress, '0xMine');

      const { validateAddress } = useGnosisPayWallet(options);
      await validateAddress();

      expect(get(options.isAddressValid)).toBe(true);
      expect(get(options.controlledSafeAddresses)).toEqual(['0xSafeA', '0xSafeC']);
      expect(options.setError).not.toHaveBeenCalled();
    });

    it('should map unexpected errors to GnosisPayError.OTHER', async () => {
      const throwingMapping: GnosisPayAdminsMapping = {};
      Object.defineProperty(throwingMapping, 'safeKey', {
        configurable: true,
        enumerable: true,
        get(): string[] {
          throw new Error('mapping access failed');
        },
      });
      const options = makeOptions({
        gnosisPayAdminsMapping: ref<GnosisPayAdminsMapping>(throwingMapping),
      });
      set(connectedAddress, '0xAddr');

      const { validateAddress } = useGnosisPayWallet(options);
      await validateAddress();

      // clearValidation should be called twice (once before validation, once in catch block)
      expect(options.clearValidation).toHaveBeenCalled();
      expect(options.setError).toHaveBeenCalledWith(
        GnosisPayError.OTHER,
        expect.objectContaining({ message: expect.any(String) }),
      );
      expect(get(options.validatingAddress)).toBe(false);
    });
  });

  describe('connect', () => {
    it('should call the wallet store connect', async () => {
      const options = makeOptions();

      const { connect } = useGnosisPayWallet(options);
      await connect();

      expect(options.clearError).toHaveBeenCalled();
      expect(options.clearValidation).toHaveBeenCalled();
      expect(connectWallet).toHaveBeenCalled();
      expect(options.setError).not.toHaveBeenCalled();
    });

    it('should set CONNECTION_FAILED when connect throws', async () => {
      connectWallet.mockRejectedValueOnce(new Error('refused'));
      const options = makeOptions();

      const { connect } = useGnosisPayWallet(options);
      await connect();

      expect(options.setError).toHaveBeenCalledWith(
        GnosisPayError.CONNECTION_FAILED,
        { message: 'refused' },
      );
    });
  });

  describe('disconnect', () => {
    it('should call the wallet store disconnect', async () => {
      const options = makeOptions();

      const { disconnect } = useGnosisPayWallet(options);
      await disconnect();

      expect(options.clearError).toHaveBeenCalled();
      expect(options.clearValidation).toHaveBeenCalled();
      expect(disconnectWallet).toHaveBeenCalled();
      expect(options.setError).not.toHaveBeenCalled();
    });

    it('should set CONNECTION_FAILED when disconnect throws', async () => {
      disconnectWallet.mockRejectedValueOnce(new Error('cannot disconnect'));
      const options = makeOptions();

      const { disconnect } = useGnosisPayWallet(options);
      await disconnect();

      expect(options.setError).toHaveBeenCalledWith(
        GnosisPayError.CONNECTION_FAILED,
        { message: 'cannot disconnect' },
      );
    });
  });
});
