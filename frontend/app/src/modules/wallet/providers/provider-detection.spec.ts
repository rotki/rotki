import type { EIP1193Provider, EIP6963ProviderDetail } from '@/types';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getAddressesFromWallet,
  getAllBrowserWalletProviders,
  getAllWalletProviders,
} from '@/modules/wallet/providers/provider-detection';

const proxyProvider = { request: vi.fn() };

vi.mock('@/modules/wallet/bridge/use-proxy-provider', () => ({
  useProxyProvider: vi.fn(() => proxyProvider),
}));

function makeDetail(uuid: string, name: string = uuid): EIP6963ProviderDetail {
  return {
    info: { icon: 'icon', name, rdns: `rdns.${uuid}`, uuid },
    provider: { request: vi.fn() },
  };
}

function announce(detail: EIP6963ProviderDetail): void {
  window.dispatchEvent(new CustomEvent('eip6963:announceProvider', { detail }));
}

function stubWindow(prop: 'ethereum' | 'walletBridge', value: unknown): void {
  Object.defineProperty(window, prop, { configurable: true, value });
}

describe('provider-detection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    Reflect.deleteProperty(window, 'ethereum');
    Reflect.deleteProperty(window, 'walletBridge');
  });

  describe('getAllWalletProviders (browser)', () => {
    it('should return announced EIP-6963 providers', async () => {
      const promise = getAllWalletProviders({ timeout: 500 });
      announce(makeDetail('u1', 'Wallet One'));
      announce(makeDetail('u2', 'Wallet Two'));
      await vi.advanceTimersByTimeAsync(500);

      const result = await promise;
      expect(result).toHaveLength(2);
      expect(result.map(p => p.info.uuid)).toEqual(['u1', 'u2']);
      expect(result[0].source).toBe('eip6963');
    });

    it('should de-duplicate providers announced twice by uuid', async () => {
      const promise = getAllWalletProviders({ timeout: 500 });
      announce(makeDetail('dup'));
      announce(makeDetail('dup'));
      await vi.advanceTimersByTimeAsync(500);

      const result = await promise;
      expect(result).toHaveLength(1);
    });

    it('should fall back to a legacy provider when none announce', async () => {
      stubWindow('ethereum', { isRotkiBridge: false, request: vi.fn() });
      const promise = getAllWalletProviders({ timeout: 200 });
      await vi.advanceTimersByTimeAsync(200); // outer eip6963 detection resolves empty
      await vi.advanceTimersByTimeAsync(100); // nested detection inside legacy check

      const result = await promise;
      expect(result).toHaveLength(1);
      expect(result[0].source).toBe('legacy');
    });

    it('should not add a legacy provider when includeLegacy is false', async () => {
      stubWindow('ethereum', { isRotkiBridge: false, request: vi.fn() });
      const promise = getAllWalletProviders({ includeLegacy: false, timeout: 200 });
      await vi.advanceTimersByTimeAsync(200);

      const result = await promise;
      expect(result).toEqual([]);
    });
  });

  describe('getAllWalletProviders (electron)', () => {
    it('should map bridge providers through the proxy provider', async () => {
      stubWindow('walletBridge', {
        getAvailableProviders: vi.fn().mockResolvedValue([makeDetail('bridge-1')]),
      });

      const result = await getAllWalletProviders();
      expect(result).toHaveLength(1);
      expect(result[0].source).toBe('bridge');
      expect(result[0].provider).toBe(proxyProvider);
    });

    it('should return empty when the bridge lookup throws', async () => {
      stubWindow('walletBridge', {
        getAvailableProviders: vi.fn().mockRejectedValue(new Error('bridge down')),
      });

      const result = await getAllWalletProviders();
      expect(result).toEqual([]);
    });
  });

  describe('getAddressesFromWallet', () => {
    it('should return the accounts from the provider', async () => {
      const request = vi.fn().mockResolvedValue(['0xabc']);
      const provider: EIP1193Provider = { request };

      await expect(getAddressesFromWallet(provider)).resolves.toEqual(['0xabc']);
      expect(request).toHaveBeenCalledWith({ method: 'eth_requestAccounts' });
    });

    it('should wrap a provider failure in a connection error', async () => {
      const provider: EIP1193Provider = { request: vi.fn().mockRejectedValue(new Error('nope')) };
      await expect(getAddressesFromWallet(provider)).rejects.toThrow('Failed to connect to wallet');
    });
  });

  describe('getAllBrowserWalletProviders', () => {
    it('should delegate to getAllWalletProviders with legacy support', async () => {
      const promise = getAllBrowserWalletProviders();
      announce(makeDetail('u1'));
      await vi.advanceTimersByTimeAsync(2000);

      const result = await promise;
      expect(result).toHaveLength(1);
    });
  });
});
