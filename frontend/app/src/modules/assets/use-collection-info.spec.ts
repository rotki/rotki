import type { AssetMap } from '@/modules/assets/types';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { assetMapping, resolveAssetIdentifier } = vi.hoisted(() => ({
  assetMapping: vi.fn<(identifiers: string[]) => Promise<AssetMap>>(),
  resolveAssetIdentifier: vi.fn<(identifier: string) => string>(identifier => identifier),
}));

vi.mock('@/modules/assets/api/use-asset-info-api', () => ({
  useAssetInfoApi: (): Record<string, unknown> => ({ assetMapping }),
}));

vi.mock('@/modules/assets/use-resolve-asset-identifier', () => ({
  useResolveAssetIdentifier: (): typeof resolveAssetIdentifier => resolveAssetIdentifier,
}));

/** The delay the composable batches over, so a test can let one batch go out. */
const BATCH_DELAY = 1600;

function mapping(assets: Record<string, string | undefined>, collections: Record<string, string> = {}): AssetMap {
  return {
    assetCollections: Object.fromEntries(
      Object.entries(collections).map(([id, mainAsset]) => [id, { mainAsset, name: id, symbol: id }]),
    ),
    assets: Object.fromEntries(
      Object.entries(assets).map(([id, collectionId]) => [
        id,
        { collectionId, isCustomAsset: false, name: id, symbol: id },
      ]),
    ),
  };
}

describe('useCollectionInfo', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    vi.clearAllMocks();
    resolveAssetIdentifier.mockImplementation(identifier => identifier);
    // `clearAllMocks` leaves a queued `...Once` implementation behind, which would leak here.
    assetMapping.mockReset();
    assetMapping.mockResolvedValue(mapping({}));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /**
   * `createSharedComposable` keeps its queues and its debounce for the life of the module, so each
   * case re-imports it rather than inheriting the last one's pending batch.
   */
  async function importFresh(): Promise<typeof import('@/modules/assets/use-collection-info')> {
    vi.resetModules();
    return import('@/modules/assets/use-collection-info');
  }

  /** Asks for the asset, lets the batch go out, then asks again for the settled answer. */
  async function collectionOf(assetId: string, ...also: string[]): Promise<string | undefined> {
    const { useCollectionInfo } = await importFresh();
    const { getCollectionId } = useCollectionInfo();

    getCollectionId(assetId);
    for (const other of also)
      getCollectionId(other);

    await vi.advanceTimersByTimeAsync(BATCH_DELAY);
    return getCollectionId(assetId);
  }

  it('should not know a collection before the batch has gone out', async () => {
    const { useCollectionInfo } = await importFresh();

    expect(useCollectionInfo().getCollectionId('ETH')).toBeUndefined();
  });

  it('should answer with the collection the backend gave', async () => {
    assetMapping.mockResolvedValue(mapping({ ETH: 'evm-eth' }));

    expect(await collectionOf('ETH')).toBe('evm-eth');
  });

  /**
   * An asset with no collection is remembered as having none, rather than left unknown: an unknown
   * asset is asked about again on every read, which is a request per render.
   */
  it('should remember that an asset has no collection', async () => {
    assetMapping.mockResolvedValue(mapping({ ETH: undefined }));

    expect(await collectionOf('ETH')).toBeNull();
  });

  /** The backend leaves out what it does not know, so the gap has to be filled in here. */
  it('should remember an asset the backend did not answer for', async () => {
    assetMapping.mockResolvedValue(mapping({}));

    expect(await collectionOf('UNKNOWN')).toBeNull();
  });

  describe('batching the requests', () => {
    it('should ask once for everything asked of it in the window', async () => {
      await collectionOf('ETH', 'BTC', 'DAI');

      expect(assetMapping).toHaveBeenCalledTimes(1);
      expect(assetMapping).toHaveBeenCalledWith(['ETH', 'BTC', 'DAI']);
    });

    it('should not ask twice for the same asset in one window', async () => {
      await collectionOf('ETH', 'ETH');

      expect(assetMapping).toHaveBeenCalledWith(['ETH']);
    });

    /**
     * A read while the batch is in flight has no answer yet, so without the in-flight guard it
     * would queue the same asset again and every render would cost another request.
     */
    it('should not ask again for an asset already in flight', async () => {
      let answer: (map: AssetMap) => void = () => {};
      assetMapping.mockImplementation(async () => new Promise<AssetMap>((resolve) => {
        answer = resolve;
      }));
      const { useCollectionInfo } = await importFresh();
      const { getCollectionId } = useCollectionInfo();
      getCollectionId('ETH');
      await vi.advanceTimersByTimeAsync(BATCH_DELAY);

      getCollectionId('ETH');
      answer(mapping({ ETH: 'evm-eth' }));
      await vi.advanceTimersByTimeAsync(BATCH_DELAY);

      expect(assetMapping).toHaveBeenCalledTimes(1);
    });

    /** Once the answer is known there is nothing left to ask. */
    it('should not ask again for an asset it already knows', async () => {
      assetMapping.mockResolvedValue(mapping({ ETH: 'evm-eth' }));
      const { useCollectionInfo } = await importFresh();
      const { getCollectionId } = useCollectionInfo();
      getCollectionId('ETH');
      await vi.advanceTimersByTimeAsync(BATCH_DELAY);
      assetMapping.mockClear();

      getCollectionId('ETH');
      await vi.advanceTimersByTimeAsync(BATCH_DELAY);

      expect(assetMapping).not.toHaveBeenCalled();
    });

    /** The backend takes 50 at a time, so a larger batch is split rather than sent whole. */
    it('should split a batch larger than the backend takes', async () => {
      const { useCollectionInfo } = await importFresh();
      const { getCollectionId } = useCollectionInfo();

      for (let i = 0; i < 120; i++)
        getCollectionId(`asset-${i}`);
      await vi.advanceTimersByTimeAsync(BATCH_DELAY);

      expect(assetMapping).toHaveBeenCalledTimes(3);
      expect(assetMapping.mock.calls[0][0]).toHaveLength(50);
      expect(assetMapping.mock.calls[2][0]).toHaveLength(20);
    });

    it('should ask nothing when nothing was queued', async () => {
      await importFresh();

      await vi.advanceTimersByTimeAsync(BATCH_DELAY);

      expect(assetMapping).not.toHaveBeenCalled();
    });
  });

  /** eth2 is the same asset as eth when the user has said so, so it is asked about under that id. */
  it('should ask under the identifier the settings resolve to', async () => {
    resolveAssetIdentifier.mockImplementation(identifier => (identifier === 'ETH2' ? 'ETH' : identifier));

    await collectionOf('ETH2');

    expect(assetMapping).toHaveBeenCalledWith(['ETH']);
  });

  describe('when a request fails', () => {
    it('should leave the asset unknown rather than remembering a wrong answer', async () => {
      assetMapping.mockRejectedValue(new Error('the backend said no'));

      expect(await collectionOf('ETH')).toBeUndefined();
    });

    /** One failed chunk must not cost the others, which were separate requests. */
    it('should keep the answers from the chunks that did work', async () => {
      assetMapping
        .mockRejectedValueOnce(new Error('the backend said no'))
        .mockResolvedValueOnce(mapping({ 'asset-60': 'late-collection' }));
      const { useCollectionInfo } = await importFresh();
      const { getCollectionId } = useCollectionInfo();

      for (let i = 0; i < 70; i++)
        getCollectionId(`asset-${i}`);
      await vi.advanceTimersByTimeAsync(BATCH_DELAY);

      expect(getCollectionId('asset-60')).toBe('late-collection');
    });
  });

  describe('the main asset of a collection', () => {
    it('should answer with the main asset the backend gave', async () => {
      assetMapping.mockResolvedValue(mapping({ ETH: 'evm-eth' }, { 'evm-eth': 'ETH' }));
      const { useCollectionInfo } = await importFresh();
      const { getCollectionId, getCollectionMainAsset } = useCollectionInfo();
      getCollectionId('ETH');
      await vi.advanceTimersByTimeAsync(BATCH_DELAY);

      expect(getCollectionMainAsset('evm-eth')).toBe('ETH');
    });

    /** A collection with no main asset is stored as null, which is not an answer to hand back. */
    it('should answer with nothing for a collection that has no main asset', async () => {
      const { useCollectionInfo } = await importFresh();

      expect(useCollectionInfo().getCollectionMainAsset('unknown-collection')).toBeUndefined();
    });
  });

  describe('the reactive readers', () => {
    it('should follow the collection arriving', async () => {
      assetMapping.mockResolvedValue(mapping({ ETH: 'evm-eth' }));
      const { useCollectionInfo } = await importFresh();
      const collection = useCollectionInfo().useCollectionId('ETH');

      expect(get(collection)).toBeUndefined();
      await vi.advanceTimersByTimeAsync(BATCH_DELAY);

      expect(get(collection)).toBe('evm-eth');
    });

    it('should follow the main asset arriving', async () => {
      assetMapping.mockResolvedValue(mapping({ ETH: 'evm-eth' }, { 'evm-eth': 'ETH' }));
      const { useCollectionInfo } = await importFresh();
      const { useCollectionId, useCollectionMainAsset } = useCollectionInfo();
      const collection = useCollectionId('ETH');
      const mainAsset = useCollectionMainAsset('evm-eth');
      get(collection);

      await vi.advanceTimersByTimeAsync(BATCH_DELAY);

      expect(get(mainAsset)).toBe('ETH');
    });
  });
});
