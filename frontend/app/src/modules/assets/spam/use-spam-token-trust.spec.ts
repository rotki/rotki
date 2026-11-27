import type { AssetWithResolutionStatus } from '@/modules/assets/use-asset-info-retrieval';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { isCuratedAssetInfo, useSpamTokenTrust } from './use-spam-token-trust';

const { getAssetInfo, isAssetWhitelisted } = vi.hoisted(() => ({
  getAssetInfo: vi.fn<(identifier: string | undefined) => AssetWithResolutionStatus | null>(),
  isAssetWhitelisted: vi.fn<(identifier: string) => boolean>(),
}));

vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: (): object => ({ isAssetWhitelisted }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({ getAssetInfo }),
}));

function assetInfo(overrides: Partial<AssetWithResolutionStatus> = {}): AssetWithResolutionStatus {
  return createMock<AssetWithResolutionStatus>({
    coingecko: undefined,
    collectionId: undefined,
    cryptocompare: undefined,
    resolved: true,
    ...overrides,
  });
}

describe('isCuratedAssetInfo', () => {
  it.each([
    { label: 'coingecko', overrides: { coingecko: 'dai' } },
    { label: 'cryptocompare', overrides: { cryptocompare: 'DAI' } },
    { label: 'collectionId', overrides: { collectionId: 'collection-1' } },
  ])('should return true for a resolved token with $label', ({ overrides }) => {
    expect(isCuratedAssetInfo(assetInfo(overrides))).toBe(true);
  });

  it('should return false for an unresolved token even with provenance fields', () => {
    expect(isCuratedAssetInfo(assetInfo({ coingecko: 'dai', resolved: false }))).toBe(false);
  });

  it('should return false for a resolved uncurated ERC-20 token', () => {
    expect(isCuratedAssetInfo(assetInfo())).toBe(false);
  });

  it.each([null, undefined])('should return false for %s', (value) => {
    expect(isCuratedAssetInfo(value)).toBe(false);
  });
});

describe('useSpamTokenTrust', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    isAssetWhitelisted.mockReturnValue(false);
    getAssetInfo.mockReturnValue(null);
  });

  it.each([undefined, null, ''])('should return false without querying stores when identifier is %s', (identifier) => {
    const { isTrustedForSpamDisplay } = useSpamTokenTrust();

    expect(isTrustedForSpamDisplay(identifier)).toBe(false);
    expect(isAssetWhitelisted).not.toHaveBeenCalled();
    expect(getAssetInfo).not.toHaveBeenCalled();
  });

  it('should trust whitelisted tokens', () => {
    isAssetWhitelisted.mockReturnValue(true);
    const { isTrustedForSpamDisplay } = useSpamTokenTrust();

    expect(isTrustedForSpamDisplay('eip155:1/erc20:0xWhitelisted')).toBe(true);
    expect(isAssetWhitelisted).toHaveBeenCalledWith('eip155:1/erc20:0xWhitelisted');
  });

  it.each([
    { label: 'coingecko', overrides: { coingecko: 'usd-coin' } },
    { label: 'cryptocompare', overrides: { cryptocompare: 'USDC' } },
    { label: 'collectionId', overrides: { collectionId: 'usdc-collection' } },
  ])('should trust resolved curated tokens with $label', ({ overrides }) => {
    getAssetInfo.mockReturnValue(assetInfo(overrides));
    const { isTrustedForSpamDisplay } = useSpamTokenTrust();

    expect(isTrustedForSpamDisplay('eip155:1/erc20:0xCurated')).toBe(true);
  });

  it('should not trust unresolved tokens', () => {
    getAssetInfo.mockReturnValue(assetInfo({ coingecko: 'usd-coin', resolved: false }));
    const { isTrustedForSpamDisplay } = useSpamTokenTrust();

    expect(isTrustedForSpamDisplay('eip155:1/erc20:0xUnresolved')).toBe(false);
  });

  it('should not trust uncurated ERC-20 tokens that are not whitelisted', () => {
    getAssetInfo.mockReturnValue(assetInfo());
    const { isTrustedForSpamDisplay } = useSpamTokenTrust();

    expect(isTrustedForSpamDisplay('eip155:1/erc20:0xUncurated')).toBe(false);
  });
});
