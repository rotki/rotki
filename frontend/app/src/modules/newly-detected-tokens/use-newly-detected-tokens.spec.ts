import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { type NewDetectedTokenInput, NewDetectedTokenKind, type NewDetectedTokensRequestPayload } from './types';

// Mock the stores
const mockIgnoredAssets = ref<string[]>([]);
const mockAddIgnoredAsset = vi.fn();

vi.mock('@/store/assets/ignored', () => ({
  useIgnoredAssetsStore: vi.fn(() => ({
    ignoredAssets: mockIgnoredAssets,
    addIgnoredAsset: mockAddIgnoredAsset,
  })),
}));

const mockNotifyNewNfts = ref<boolean>(true);

vi.mock('@/store/settings/frontend', () => ({
  useFrontendSettingsStore: vi.fn(() => ({
    notifyNewNfts: mockNotifyNewNfts,
  })),
}));

// Mock the database composable
const mockAddToken = vi.fn();
const mockRemoveTokens = vi.fn();
const mockClearAll = vi.fn();
const mockCount = vi.fn();
const mockGetAllIdentifiers = vi.fn();
const mockGetData = vi.fn();
const mockIsReady = ref<boolean>(true);

vi.mock('./use-newly-detected-tokens-db', () => ({
  useNewlyDetectedTokensDb: vi.fn(() => ({
    addToken: mockAddToken,
    clearAll: mockClearAll,
    count: mockCount,
    getAllIdentifiers: mockGetAllIdentifiers,
    getData: mockGetData,
    isReady: mockIsReady,
    removeTokens: mockRemoveTokens,
  })),
}));

// Import after mocks
const { useNewlyDetectedTokens } = await import('./use-newly-detected-tokens');

describe('useNewlyDetectedTokens', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIgnoredAssets.value = [];
    mockNotifyNewNfts.value = true;
    mockIsReady.value = true;
    mockAddToken.mockResolvedValue(true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('addNewDetectedToken', () => {
    it('should add a regular EVM token', async () => {
      const { addNewDetectedToken } = useNewlyDetectedTokens();

      const token: NewDetectedTokenInput = {
        tokenIdentifier: 'eip155:1/erc20:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
      };

      const result = await addNewDetectedToken(token);

      expect(result).toBe(true);
      expect(mockAddToken).toHaveBeenCalledWith(token);
    });

    it('should not add NFT token when notifyNewNfts is disabled', async () => {
      mockNotifyNewNfts.value = false;
      const { addNewDetectedToken } = useNewlyDetectedTokens();

      const token: NewDetectedTokenInput = {
        tokenIdentifier: 'eip155:1/erc721:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
      };

      const result = await addNewDetectedToken(token);

      expect(result).toBe(false);
      expect(mockAddToken).not.toHaveBeenCalled();
    });

    it('should add NFT token when notifyNewNfts is enabled', async () => {
      mockNotifyNewNfts.value = true;
      const { addNewDetectedToken } = useNewlyDetectedTokens();

      const token: NewDetectedTokenInput = {
        tokenIdentifier: 'eip155:1/erc721:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
      };

      const result = await addNewDetectedToken(token);

      expect(result).toBe(true);
      expect(mockAddToken).toHaveBeenCalledWith(token);
    });

    it('should add to ignored assets when token is marked as ignored', async () => {
      const { addNewDetectedToken } = useNewlyDetectedTokens();

      const token: NewDetectedTokenInput = {
        tokenIdentifier: 'eip155:1/erc20:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
        isIgnored: true,
      };

      const result = await addNewDetectedToken(token);

      expect(result).toBe(false);
      expect(mockAddIgnoredAsset).toHaveBeenCalledWith('eip155:1/erc20:0x1234');
      expect(mockAddToken).not.toHaveBeenCalled();
    });
  });

  describe('removeNewDetectedTokens', () => {
    it('should call removeTokens with identifiers', async () => {
      const { removeNewDetectedTokens } = useNewlyDetectedTokens();

      await removeNewDetectedTokens(['token1', 'token2']);

      expect(mockRemoveTokens).toHaveBeenCalledWith(['token1', 'token2']);
    });
  });

  describe('clearInternalTokens', () => {
    it('should call clearAll', async () => {
      const { clearInternalTokens } = useNewlyDetectedTokens();

      await clearInternalTokens();

      expect(mockClearAll).toHaveBeenCalled();
    });
  });

  describe('count', () => {
    it('should return count from db', async () => {
      mockCount.mockResolvedValue(42);
      const { count } = useNewlyDetectedTokens();

      const result = await count();

      expect(result).toBe(42);
      expect(mockCount).toHaveBeenCalled();
    });
  });

  describe('getAllIdentifiers', () => {
    it('should return identifiers from db', async () => {
      mockGetAllIdentifiers.mockResolvedValue(['token1', 'token2']);
      const { getAllIdentifiers } = useNewlyDetectedTokens();

      const result = await getAllIdentifiers();

      expect(result).toEqual(['token1', 'token2']);
      expect(mockGetAllIdentifiers).toHaveBeenCalled();
    });

    it('should pass tokenKind filter to db', async () => {
      mockGetAllIdentifiers.mockResolvedValue(['solana-token']);
      const { getAllIdentifiers } = useNewlyDetectedTokens();

      const result = await getAllIdentifiers(NewDetectedTokenKind.SOLANA);

      expect(result).toEqual(['solana-token']);
      expect(mockGetAllIdentifiers).toHaveBeenCalledWith(NewDetectedTokenKind.SOLANA);
    });
  });

  describe('getData', () => {
    it('should return collection data from db', async () => {
      const mockData = {
        data: [{ tokenIdentifier: 'token1', tokenKind: NewDetectedTokenKind.EVM, detectedAt: Date.now() }],
        found: 1,
        limit: -1,
        total: 1,
      };
      mockGetData.mockResolvedValue(mockData);
      const { getData } = useNewlyDetectedTokens();

      const payload: NewDetectedTokensRequestPayload = {
        limit: 10,
        offset: 0,
        orderByAttributes: ['detectedAt'],
        ascending: [false],
      };
      const result = await getData(payload);

      expect(result).toEqual(mockData);
      expect(mockGetData).toHaveBeenCalledWith(payload);
    });
  });

  describe('isReady', () => {
    it('should expose isReady ref from db', () => {
      const { isReady } = useNewlyDetectedTokens();

      expect(isReady.value).toBe(true);

      mockIsReady.value = false;
      expect(isReady.value).toBe(false);
    });
  });
});
