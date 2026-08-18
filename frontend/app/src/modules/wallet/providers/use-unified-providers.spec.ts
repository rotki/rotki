import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EnhancedProviderDetail, getAllWalletProviders } from '@/modules/wallet/providers/provider-detection';
import { useUnifiedProviders } from '@/modules/wallet/providers/use-unified-providers';

vi.mock('@/modules/wallet/providers/provider-detection', () => ({
  getAllWalletProviders: vi.fn(),
}));

vi.mock('@shared/utils', async (importOriginal): Promise<any> => ({
  ...(await importOriginal<any>()),
  wait: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('@vueuse/core', async (importOriginal): Promise<any> => ({
  ...(await importOriginal<any>()),
  createSharedComposable: <T>(fn: T): T => fn,
}));

const detectMock = vi.mocked(getAllWalletProviders);

function makeProvider(
  uuid: string,
  source: EnhancedProviderDetail['source'] = 'eip6963',
  name: string = uuid,
): EnhancedProviderDetail {
  return {
    info: { icon: 'icon', name, rdns: `rdns.${uuid}`, uuid },
    provider: { request: vi.fn() },
    source,
  };
}

function stubWalletBridge(value: Record<string, unknown>): void {
  Object.defineProperty(window, 'walletBridge', { configurable: true, value });
}

describe('useUnifiedProviders', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    detectMock.mockResolvedValue([]);
  });

  afterEach(() => {
    Reflect.deleteProperty(window, 'walletBridge');
  });

  it('should default to empty state', () => {
    const { availableProviders, hasSelectedProvider, isDetecting, selectedProviderUuid } = useUnifiedProviders();
    expect(get(availableProviders)).toEqual([]);
    expect(get(hasSelectedProvider)).toBe(false);
    expect(get(isDetecting)).toBe(false);
    expect(get(selectedProviderUuid)).toBeUndefined();
  });

  it('should store detected providers without auto-selecting when multiple exist', async () => {
    detectMock.mockResolvedValue([makeProvider('a'), makeProvider('b')]);
    const { availableProviders, detectProviders, hasSelectedProvider } = useUnifiedProviders();

    const result = await detectProviders();

    expect(result).toHaveLength(2);
    expect(get(availableProviders)).toHaveLength(2);
    expect(get(hasSelectedProvider)).toBe(false);
  });

  it('should auto-select the sole detected provider', async () => {
    detectMock.mockResolvedValue([makeProvider('solo', 'eip6963', 'Solo Wallet')]);
    const { activeProvider, detectProviders, hasSelectedProvider, selectedProviderMetadata, selectedProviderUuid } = useUnifiedProviders();

    await detectProviders();

    expect(get(hasSelectedProvider)).toBe(true);
    expect(get(selectedProviderUuid)).toBe('solo');
    expect(get(selectedProviderMetadata)?.name).toBe('Solo Wallet');
    expect(get(activeProvider)).toBeDefined();
  });

  it('should retry detection until providers appear', async () => {
    detectMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([makeProvider('a')]);
    const { detectProviders } = useUnifiedProviders();

    await detectProviders({ maxRetries: 3 });

    expect(detectMock).toHaveBeenCalledTimes(2);
  });

  it('should stop retrying after maxRetries and return empty', async () => {
    detectMock.mockResolvedValue([]);
    const { availableProviders, detectProviders } = useUnifiedProviders();

    const result = await detectProviders({ maxRetries: 1 });

    expect(result).toEqual([]);
    expect(detectMock).toHaveBeenCalledTimes(2);
    expect(get(availableProviders)).toEqual([]);
  });

  it('should swallow a failing detection and record the error state', async () => {
    detectMock.mockRejectedValue(new Error('detect failed'));
    const { availableProviders, detectProviders, isDetecting } = useUnifiedProviders();

    const result = await detectProviders({ maxRetries: 1 });

    expect(result).toEqual([]);
    expect(get(availableProviders)).toEqual([]);
    expect(get(isDetecting)).toBe(false);
    expect(detectMock).toHaveBeenCalledTimes(2);
  });

  it('should return false when selecting an unknown provider', async () => {
    detectMock.mockResolvedValue([makeProvider('a'), makeProvider('b')]);
    const { detectProviders, selectProvider } = useUnifiedProviders();
    await detectProviders();

    await expect(selectProvider('missing')).resolves.toBe(false);
  });

  it('should select a provider, persist the choice and notify listeners', async () => {
    detectMock.mockResolvedValue([makeProvider('a'), makeProvider('b')]);
    const { detectProviders, onProviderChanged, selectProvider, selectedProviderUuid } = useUnifiedProviders();
    await detectProviders();

    const listener = vi.fn();
    onProviderChanged(listener);

    const ok = await selectProvider('b');

    expect(ok).toBe(true);
    expect(get(selectedProviderUuid)).toBe('b');
    expect(listener).toHaveBeenCalledOnce();
    const stored = JSON.parse(localStorage.getItem('rotki-provider-preferences') ?? '{}');
    expect(stored.lastSelectedUuid).toBe('b');
  });

  it('should stop notifying after the listener cleanup runs', async () => {
    detectMock.mockResolvedValue([makeProvider('a'), makeProvider('b')]);
    const { detectProviders, onProviderChanged, selectProvider } = useUnifiedProviders();
    await detectProviders();

    const listener = vi.fn();
    const off = onProviderChanged(listener);
    off();

    await selectProvider('a');
    expect(listener).not.toHaveBeenCalled();
  });

  it('should clear the selection and notify listeners with undefined', async () => {
    detectMock.mockResolvedValue([makeProvider('solo')]);
    const { clearProvider, detectProviders, hasSelectedProvider, onProviderChanged } = useUnifiedProviders();
    await detectProviders();
    expect(get(hasSelectedProvider)).toBe(true);

    const listener = vi.fn();
    onProviderChanged(listener);
    clearProvider();

    expect(get(hasSelectedProvider)).toBe(false);
    expect(listener).toHaveBeenCalledWith(undefined, expect.anything());
  });

  it('should forget the remembered provider when clearing deliberately', async () => {
    detectMock.mockResolvedValue([makeProvider('solo')]);
    const { clearProvider, detectProviders } = useUnifiedProviders();
    await detectProviders();
    expect(JSON.parse(localStorage.getItem('rotki-provider-preferences') ?? '{}').lastSelectedUuid).toBe('solo');

    clearProvider();
    await nextTick(); // useLocalStorage flushes on 'pre'

    expect(JSON.parse(localStorage.getItem('rotki-provider-preferences') ?? '{}').lastSelectedUuid).toBeUndefined();
  });

  it('should keep the remembered provider when clearing without forgetting', async () => {
    detectMock.mockResolvedValue([makeProvider('solo')]);
    const { clearProvider, detectProviders, hasSelectedProvider } = useUnifiedProviders();
    await detectProviders();

    clearProvider({ forget: false });
    await nextTick(); // useLocalStorage flushes on 'pre'

    // the active selection still goes away, only the persisted choice survives
    expect(get(hasSelectedProvider)).toBe(false);
    expect(JSON.parse(localStorage.getItem('rotki-provider-preferences') ?? '{}').lastSelectedUuid).toBe('solo');
  });

  it('should clear the selection when selecting the empty uuid', async () => {
    detectMock.mockResolvedValue([makeProvider('solo')]);
    const { detectProviders, hasSelectedProvider, selectProvider } = useUnifiedProviders();
    await detectProviders();

    await expect(selectProvider('')).resolves.toBe(true);
    expect(get(hasSelectedProvider)).toBe(false);
  });

  it('should restore the previously selected provider on detection', async () => {
    localStorage.setItem('rotki-provider-preferences', JSON.stringify({ autoSelectSingle: true, lastSelectedUuid: 'b' }));
    detectMock.mockResolvedValue([makeProvider('a'), makeProvider('b')]);
    const { detectProviders, selectedProviderUuid } = useUnifiedProviders();

    await detectProviders();

    expect(get(selectedProviderUuid)).toBe('b');
  });

  it('should prompt for selection when multiple bridge providers exist in electron mode', async () => {
    stubWalletBridge({});
    detectMock.mockResolvedValue([makeProvider('a', 'bridge'), makeProvider('b', 'bridge')]);
    const { detectProviders, hasSelectedProvider, showProviderSelection } = useUnifiedProviders();

    await detectProviders();

    expect(get(showProviderSelection)).toBe(true);
    expect(get(hasSelectedProvider)).toBe(false);
  });

  it('should notify the bridge when a bridge provider is selected', async () => {
    const selectProviderOnBridge = vi.fn().mockResolvedValue(undefined);
    stubWalletBridge({ selectProvider: selectProviderOnBridge });
    detectMock.mockResolvedValue([makeProvider('a', 'bridge'), makeProvider('b', 'bridge')]);
    const { detectProviders, selectProvider } = useUnifiedProviders();
    await detectProviders();

    const ok = await selectProvider('a');

    expect(ok).toBe(true);
    expect(selectProviderOnBridge).toHaveBeenCalledWith('a');
  });

  it('should return false when the bridge rejects the selection', async () => {
    const selectProviderOnBridge = vi.fn().mockRejectedValue(new Error('bridge down'));
    stubWalletBridge({ selectProvider: selectProviderOnBridge });
    detectMock.mockResolvedValue([makeProvider('a', 'bridge'), makeProvider('b', 'bridge')]);
    const { detectProviders, selectProvider } = useUnifiedProviders();
    await detectProviders();

    await expect(selectProvider('a')).resolves.toBe(false);
  });

  it('should report selection state via the bridge in electron mode', async () => {
    const getSelectedProvider = vi.fn().mockResolvedValue({ info: {} });
    stubWalletBridge({ getSelectedProvider });
    const { checkIfSelectedProvider } = useUnifiedProviders();

    await expect(checkIfSelectedProvider()).resolves.toBe(true);

    getSelectedProvider.mockResolvedValue(null);
    await expect(checkIfSelectedProvider()).resolves.toBe(false);
  });

  it('should return false when the bridge selection check throws', async () => {
    const getSelectedProvider = vi.fn().mockRejectedValue(new Error('boom'));
    stubWalletBridge({ getSelectedProvider });
    const { checkIfSelectedProvider } = useUnifiedProviders();

    await expect(checkIfSelectedProvider()).resolves.toBe(false);
  });

  it('should fall back to local selection state in browser mode', async () => {
    detectMock.mockResolvedValue([makeProvider('solo')]);
    const { checkIfSelectedProvider, detectProviders } = useUnifiedProviders();
    await detectProviders();

    await expect(checkIfSelectedProvider()).resolves.toBe(true);
  });

  it('should reset all state on cleanup', async () => {
    detectMock.mockResolvedValue([makeProvider('solo')]);
    const { availableProviders, cleanup, detectProviders, hasSelectedProvider } = useUnifiedProviders();
    await detectProviders();
    expect(get(hasSelectedProvider)).toBe(true);

    cleanup();

    expect(get(availableProviders)).toEqual([]);
    expect(get(hasSelectedProvider)).toBe(false);
  });
});
