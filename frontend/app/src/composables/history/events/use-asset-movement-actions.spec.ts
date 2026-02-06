import type { UnmatchedAssetMovement } from '@/composables/history/events/use-unmatched-asset-movements';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetMovementActions } from '@/composables/history/events/use-asset-movement-actions';

const { spies } = vi.hoisted(() => ({
  spies: {
    matchAssetMovements: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    unlinkAssetMovement: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    refreshUnmatchedAssetMovements: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
    showConfirm: vi.fn(),
  },
}));

const unmatchedMovementsRef = ref<UnmatchedAssetMovement[]>([]);
const ignoredMovementsRef = ref<UnmatchedAssetMovement[]>([]);

vi.mock('@/composables/api/history/events/asset-movement-matching', () => ({
  useAssetMovementMatchingApi: (): object => ({
    matchAssetMovements: spies.matchAssetMovements,
    unlinkAssetMovement: spies.unlinkAssetMovement,
  }),
}));

vi.mock('@/composables/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): object => ({
    unmatchedMovements: computed<UnmatchedAssetMovement[]>(() => get(unmatchedMovementsRef)),
    ignoredMovements: computed<UnmatchedAssetMovement[]>(() => get(ignoredMovementsRef)),
    refreshUnmatchedAssetMovements: spies.refreshUnmatchedAssetMovements,
  }),
}));

vi.mock('@/store/confirm', () => ({
  useConfirmStore: (): object => ({
    show: spies.showConfirm,
  }),
}));

vi.mock('@/utils/history/events', () => ({
  getEventEntryFromCollection: <T>(events: T): T => events,
}));

function createMockMovement(overrides: {
  groupIdentifier?: string;
  identifier?: number;
  asset?: string;
  isFiat?: boolean;
} = {}): UnmatchedAssetMovement {
  return {
    groupIdentifier: overrides.groupIdentifier ?? 'group1',
    events: { entry: { identifier: overrides.identifier ?? 1 } } as unknown as UnmatchedAssetMovement['events'],
    asset: overrides.asset ?? 'ETH',
    isFiat: overrides.isFiat ?? false,
  };
}

interface SetupResult {
  composable: ReturnType<typeof useAssetMovementActions>;
  onActionComplete: ReturnType<typeof vi.fn>;
}

function setupWithCallback(): SetupResult {
  const onActionComplete = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  const composable = useAssetMovementActions({ onActionComplete });
  return { composable, onActionComplete };
}

function setupWithoutCallback(): ReturnType<typeof useAssetMovementActions> {
  return useAssetMovementActions();
}

async function extractAndCallConfirmCallback(): Promise<void> {
  const callback = spies.showConfirm.mock.calls[0][1] as () => Promise<void>;
  await callback();
}

describe('use-asset-movement-actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(unmatchedMovementsRef, []);
    set(ignoredMovementsRef, []);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('return value', () => {
    it('should return all expected properties', () => {
      const composable = setupWithoutCallback();

      expect(composable).toHaveProperty('fiatMovements');
      expect(composable).toHaveProperty('ignoreLoading');
      expect(composable).toHaveProperty('selectedIgnored');
      expect(composable).toHaveProperty('selectedUnmatched');
      expect(composable).toHaveProperty('confirmIgnoreAllFiat');
      expect(composable).toHaveProperty('confirmIgnoreSelected');
      expect(composable).toHaveProperty('confirmRestoreSelected');
      expect(composable).toHaveProperty('ignoreMovement');
      expect(composable).toHaveProperty('restoreMovement');
    });

    it('should initialize refs with default values', () => {
      const composable = setupWithoutCallback();

      expect(get(composable.ignoreLoading)).toBe(false);
      expect(get(composable.selectedUnmatched)).toEqual([]);
      expect(get(composable.selectedIgnored)).toEqual([]);
    });
  });

  describe('fiatMovements', () => {
    it('should filter unmatched movements by isFiat', () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', isFiat: true, asset: 'USD' }),
        createMockMovement({ groupIdentifier: 'g2', isFiat: false, asset: 'ETH' }),
        createMockMovement({ groupIdentifier: 'g3', isFiat: true, asset: 'EUR' }),
      ]);

      const { fiatMovements } = setupWithoutCallback();
      const result = get(fiatMovements);

      expect(result).toHaveLength(2);
      expect(result[0].asset).toBe('USD');
      expect(result[1].asset).toBe('EUR');
    });

    it('should return empty array when no fiat movements exist', () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: false }),
      ]);

      const { fiatMovements } = setupWithoutCallback();

      expect(get(fiatMovements)).toHaveLength(0);
    });
  });

  describe('ignoreMovement', () => {
    it('should call matchAssetMovements with correct identifier', async () => {
      const movement = createMockMovement({ identifier: 42 });
      const { composable } = setupWithCallback();

      await composable.ignoreMovement(movement);

      expect(spies.matchAssetMovements).toHaveBeenCalledWith(42);
    });

    it('should refresh and call onActionComplete on success', async () => {
      const movement = createMockMovement();
      const { composable, onActionComplete } = setupWithCallback();

      await composable.ignoreMovement(movement);

      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(onActionComplete).toHaveBeenCalledOnce();
    });

    it('should set ignoreLoading during operation and reset after', async () => {
      const movement = createMockMovement();
      const { composable } = setupWithCallback();

      const loadingDuringCall: boolean[] = [];
      spies.matchAssetMovements.mockImplementation(async () => {
        loadingDuringCall.push(get(composable.ignoreLoading));
        return Promise.resolve(true);
      });

      await composable.ignoreMovement(movement);

      expect(loadingDuringCall[0]).toBe(true);
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should reset ignoreLoading on error', async () => {
      const movement = createMockMovement();
      spies.matchAssetMovements.mockRejectedValueOnce(new Error('API error'));
      const { composable } = setupWithCallback();

      await expect(composable.ignoreMovement(movement)).rejects.toThrow('API error');

      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should work without onActionComplete callback', async () => {
      const movement = createMockMovement({ identifier: 10 });
      const composable = setupWithoutCallback();

      await composable.ignoreMovement(movement);

      expect(spies.matchAssetMovements).toHaveBeenCalledWith(10);
      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
    });
  });

  describe('restoreMovement', () => {
    it('should call unlinkAssetMovement with correct identifier', async () => {
      const movement = createMockMovement({ identifier: 55 });
      const { composable } = setupWithCallback();

      await composable.restoreMovement(movement);

      expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(55);
    });

    it('should refresh and call onActionComplete on success', async () => {
      const movement = createMockMovement();
      const { composable, onActionComplete } = setupWithCallback();

      await composable.restoreMovement(movement);

      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(onActionComplete).toHaveBeenCalledOnce();
    });

    it('should set ignoreLoading during operation and reset after', async () => {
      const movement = createMockMovement();
      const { composable } = setupWithCallback();

      const loadingDuringCall: boolean[] = [];
      spies.unlinkAssetMovement.mockImplementation(async () => {
        loadingDuringCall.push(get(composable.ignoreLoading));
        return Promise.resolve(true);
      });

      await composable.restoreMovement(movement);

      expect(loadingDuringCall[0]).toBe(true);
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should reset ignoreLoading on error', async () => {
      const movement = createMockMovement();
      spies.unlinkAssetMovement.mockRejectedValueOnce(new Error('API error'));
      const { composable } = setupWithCallback();

      await expect(composable.restoreMovement(movement)).rejects.toThrow('API error');

      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should work without onActionComplete callback', async () => {
      const movement = createMockMovement({ identifier: 20 });
      const composable = setupWithoutCallback();

      await composable.restoreMovement(movement);

      expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(20);
      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
    });
  });

  describe('confirmIgnoreSelected', () => {
    it('should show confirm dialog with correct message', () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
        createMockMovement({ groupIdentifier: 'g2', identifier: 2 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedUnmatched, ['g1', 'g2']);
      composable.confirmIgnoreSelected();

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('callback should call matchAssetMovements for each selected movement', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 10 }),
        createMockMovement({ groupIdentifier: 'g2', identifier: 20 }),
        createMockMovement({ groupIdentifier: 'g3', identifier: 30 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedUnmatched, ['g1', 'g3']);
      composable.confirmIgnoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.matchAssetMovements).toHaveBeenCalledTimes(2);
      expect(spies.matchAssetMovements).toHaveBeenCalledWith(10);
      expect(spies.matchAssetMovements).toHaveBeenCalledWith(30);
    });

    it('callback should refresh and clear selectedUnmatched', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedUnmatched, ['g1']);
      composable.confirmIgnoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.selectedUnmatched)).toEqual([]);
    });

    it('callback should reset ignoreLoading on error', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);
      spies.matchAssetMovements.mockRejectedValueOnce(new Error('fail'));

      const composable = setupWithoutCallback();
      set(composable.selectedUnmatched, ['g1']);
      composable.confirmIgnoreSelected();

      await expect(extractAndCallConfirmCallback()).rejects.toThrow('fail');
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('callback should still refresh and clear selection when no movements match', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedUnmatched, ['non-existent']);
      composable.confirmIgnoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.matchAssetMovements).not.toHaveBeenCalled();
      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.selectedUnmatched)).toEqual([]);
    });

    it('callback should set ignoreLoading during batch operation', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
        createMockMovement({ groupIdentifier: 'g2', identifier: 2 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedUnmatched, ['g1', 'g2']);

      const loadingDuringCall: boolean[] = [];
      spies.matchAssetMovements.mockImplementation(async () => {
        loadingDuringCall.push(get(composable.ignoreLoading));
        return Promise.resolve(true);
      });

      composable.confirmIgnoreSelected();
      await extractAndCallConfirmCallback();

      expect(loadingDuringCall).toEqual([true, true]);
      expect(get(composable.ignoreLoading)).toBe(false);
    });
  });

  describe('confirmRestoreSelected', () => {
    it('should show confirm dialog with correct message', () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedIgnored, ['g1']);
      composable.confirmRestoreSelected();

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('callback should call unlinkAssetMovement for each selected ignored movement', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 10 }),
        createMockMovement({ groupIdentifier: 'g2', identifier: 20 }),
        createMockMovement({ groupIdentifier: 'g3', identifier: 30 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedIgnored, ['g2', 'g3']);
      composable.confirmRestoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.unlinkAssetMovement).toHaveBeenCalledTimes(2);
      expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(20);
      expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(30);
    });

    it('callback should refresh and clear selectedIgnored', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedIgnored, ['g1']);
      composable.confirmRestoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.selectedIgnored)).toEqual([]);
    });

    it('callback should reset ignoreLoading on error', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);
      spies.unlinkAssetMovement.mockRejectedValueOnce(new Error('fail'));

      const composable = setupWithoutCallback();
      set(composable.selectedIgnored, ['g1']);
      composable.confirmRestoreSelected();

      await expect(extractAndCallConfirmCallback()).rejects.toThrow('fail');
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('callback should still refresh and clear selection when no movements match', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedIgnored, ['non-existent']);
      composable.confirmRestoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.unlinkAssetMovement).not.toHaveBeenCalled();
      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.selectedIgnored)).toEqual([]);
    });

    it('callback should set ignoreLoading during batch operation', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
        createMockMovement({ groupIdentifier: 'g2', identifier: 2 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedIgnored, ['g1', 'g2']);

      const loadingDuringCall: boolean[] = [];
      spies.unlinkAssetMovement.mockImplementation(async () => {
        loadingDuringCall.push(get(composable.ignoreLoading));
        return Promise.resolve(true);
      });

      composable.confirmRestoreSelected();
      await extractAndCallConfirmCallback();

      expect(loadingDuringCall).toEqual([true, true]);
      expect(get(composable.ignoreLoading)).toBe(false);
    });
  });

  describe('confirmIgnoreAllFiat', () => {
    it('should show confirm dialog with correct message', () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: true, asset: 'USD' }),
        createMockMovement({ isFiat: true, asset: 'EUR' }),
        createMockMovement({ isFiat: false, asset: 'ETH' }),
      ]);

      const composable = setupWithoutCallback();
      composable.confirmIgnoreAllFiat();

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('callback should call matchAssetMovements for each fiat movement', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: true, identifier: 10 }),
        createMockMovement({ isFiat: false, identifier: 20 }),
        createMockMovement({ isFiat: true, identifier: 30 }),
      ]);

      const composable = setupWithoutCallback();
      composable.confirmIgnoreAllFiat();
      await extractAndCallConfirmCallback();

      expect(spies.matchAssetMovements).toHaveBeenCalledTimes(2);
      expect(spies.matchAssetMovements).toHaveBeenCalledWith(10);
      expect(spies.matchAssetMovements).toHaveBeenCalledWith(30);
    });

    it('callback should refresh and clear selectedUnmatched', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: true, identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedUnmatched, ['g1']);
      composable.confirmIgnoreAllFiat();
      await extractAndCallConfirmCallback();

      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.selectedUnmatched)).toEqual([]);
    });

    it('callback should reset ignoreLoading on error', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: true, identifier: 1 }),
      ]);
      spies.matchAssetMovements.mockRejectedValueOnce(new Error('fail'));

      const composable = setupWithoutCallback();
      composable.confirmIgnoreAllFiat();

      await expect(extractAndCallConfirmCallback()).rejects.toThrow('fail');
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('callback should still refresh and clear selection when no fiat movements exist', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: false, identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.selectedUnmatched, ['g1']);
      composable.confirmIgnoreAllFiat();
      await extractAndCallConfirmCallback();

      expect(spies.matchAssetMovements).not.toHaveBeenCalled();
      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.selectedUnmatched)).toEqual([]);
    });

    it('callback should set ignoreLoading during batch operation', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: true, identifier: 1 }),
        createMockMovement({ isFiat: true, identifier: 2 }),
      ]);

      const composable = setupWithoutCallback();

      const loadingDuringCall: boolean[] = [];
      spies.matchAssetMovements.mockImplementation(async () => {
        loadingDuringCall.push(get(composable.ignoreLoading));
        return Promise.resolve(true);
      });

      composable.confirmIgnoreAllFiat();
      await extractAndCallConfirmCallback();

      expect(loadingDuringCall).toEqual([true, true]);
      expect(get(composable.ignoreLoading)).toBe(false);
    });
  });
});
