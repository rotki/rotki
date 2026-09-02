import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetMovementActions } from '@/modules/history/events/use-asset-movement-actions';

const { spies } = vi.hoisted(() => ({
  spies: {
    matchAssetMovements: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    unlinkAssetMovement: vi.fn<(id: number) => Promise<boolean>>().mockResolvedValue(true),
    refreshUnmatchedAssetMovements: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
    resolveExternal: vi.fn<(id: number) => Promise<{ message: string; success: boolean }>>().mockResolvedValue({ message: '', success: true }),
    showConfirm: vi.fn(),
  },
}));

const unmatchedMovementsRef = ref<UnmatchedAssetMovement[]>([]);
const ignoredMovementsRef = ref<UnmatchedAssetMovement[]>([]);

vi.mock('@/modules/history/api/events/use-asset-movement-matching-api', () => ({
  useAssetMovementMatchingApi: (): object => ({
    matchAssetMovements: spies.matchAssetMovements,
    unlinkAssetMovement: spies.unlinkAssetMovement,
  }),
}));

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): object => ({
    unmatchedMovements: computed<UnmatchedAssetMovement[]>(() => get(unmatchedMovementsRef)),
    ignoredMovements: computed<UnmatchedAssetMovement[]>(() => get(ignoredMovementsRef)),
    refreshUnmatchedAssetMovements: spies.refreshUnmatchedAssetMovements,
    resolveExternal: spies.resolveExternal,
  }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({
    show: spies.showConfirm,
  }),
}));

vi.mock('@/modules/history/event-utils', () => ({
  getEventEntryFromCollection: <T>(events: T): T => events,
}));

function createMockMovement(overrides: {
  groupIdentifier?: string;
  identifier?: number;
  asset?: string;
  isFiat?: boolean;
  eventSubtype?: string;
} = {}): UnmatchedAssetMovement {
  return {
    groupIdentifier: overrides.groupIdentifier ?? 'group1',
    // @ts-expect-error partial mock for testing - only identifier and subtype are read
    events: { entry: { identifier: overrides.identifier ?? 1, eventSubtype: overrides.eventSubtype ?? 'spend' } },
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
  const callback: unknown = spies.showConfirm.mock.calls[0][1];
  if (typeof callback !== 'function')
    throw new Error('Expected callback function');
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
      expect(composable).toHaveProperty('modelSelectedIgnored');
      expect(composable).toHaveProperty('modelSelectedUnmatched');
      expect(composable).toHaveProperty('confirmIgnoreAllFiat');
      expect(composable).toHaveProperty('confirmIgnoreSelected');
      expect(composable).toHaveProperty('confirmRestoreSelected');
      expect(composable).toHaveProperty('ignoreMovement');
      expect(composable).toHaveProperty('markExternal');
      expect(composable).toHaveProperty('restoreMovement');
      expect(composable).toHaveProperty('resolutionNotice');
      expect(composable).toHaveProperty('dismissResolution');
      expect(composable).toHaveProperty('undoResolution');
    });

    it('should initialize refs with default values', () => {
      const composable = setupWithoutCallback();

      expect(get(composable.ignoreLoading)).toBe(false);
      expect(get(composable.modelSelectedUnmatched)).toEqual([]);
      expect(get(composable.modelSelectedIgnored)).toEqual([]);
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
      set(composable.modelSelectedUnmatched, ['g1', 'g2']);
      composable.confirmIgnoreSelected();

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('should call matchAssetMovements for each selected movement', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 10 }),
        createMockMovement({ groupIdentifier: 'g2', identifier: 20 }),
        createMockMovement({ groupIdentifier: 'g3', identifier: 30 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedUnmatched, ['g1', 'g3']);
      composable.confirmIgnoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.matchAssetMovements).toHaveBeenCalledTimes(2);
      expect(spies.matchAssetMovements).toHaveBeenCalledWith(10);
      expect(spies.matchAssetMovements).toHaveBeenCalledWith(30);
    });

    it('should refresh and clear modelSelectedUnmatched', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedUnmatched, ['g1']);
      composable.confirmIgnoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.modelSelectedUnmatched)).toEqual([]);
    });

    it('should reset ignoreLoading on error', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);
      spies.matchAssetMovements.mockRejectedValueOnce(new Error('fail'));

      const composable = setupWithoutCallback();
      set(composable.modelSelectedUnmatched, ['g1']);
      composable.confirmIgnoreSelected();

      await expect(extractAndCallConfirmCallback()).rejects.toThrow('fail');
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should still refresh and clear selection when no movements match', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedUnmatched, ['non-existent']);
      composable.confirmIgnoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.matchAssetMovements).not.toHaveBeenCalled();
      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.modelSelectedUnmatched)).toEqual([]);
    });

    it('should set ignoreLoading during batch operation', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
        createMockMovement({ groupIdentifier: 'g2', identifier: 2 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedUnmatched, ['g1', 'g2']);

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
      set(composable.modelSelectedIgnored, ['g1']);
      composable.confirmRestoreSelected();

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('should call unlinkAssetMovement for each selected ignored movement', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 10 }),
        createMockMovement({ groupIdentifier: 'g2', identifier: 20 }),
        createMockMovement({ groupIdentifier: 'g3', identifier: 30 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedIgnored, ['g2', 'g3']);
      composable.confirmRestoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.unlinkAssetMovement).toHaveBeenCalledTimes(2);
      expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(20);
      expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(30);
    });

    it('should refresh and clear modelSelectedIgnored', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedIgnored, ['g1']);
      composable.confirmRestoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.modelSelectedIgnored)).toEqual([]);
    });

    it('should reset ignoreLoading on error', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);
      spies.unlinkAssetMovement.mockRejectedValueOnce(new Error('fail'));

      const composable = setupWithoutCallback();
      set(composable.modelSelectedIgnored, ['g1']);
      composable.confirmRestoreSelected();

      await expect(extractAndCallConfirmCallback()).rejects.toThrow('fail');
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should still refresh and clear selection when no movements match', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedIgnored, ['non-existent']);
      composable.confirmRestoreSelected();
      await extractAndCallConfirmCallback();

      expect(spies.unlinkAssetMovement).not.toHaveBeenCalled();
      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.modelSelectedIgnored)).toEqual([]);
    });

    it('should set ignoreLoading during batch operation', async () => {
      set(ignoredMovementsRef, [
        createMockMovement({ groupIdentifier: 'g1', identifier: 1 }),
        createMockMovement({ groupIdentifier: 'g2', identifier: 2 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedIgnored, ['g1', 'g2']);

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

    it('should call matchAssetMovements for each fiat movement', async () => {
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

    it('should refresh and clear modelSelectedUnmatched', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: true, identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedUnmatched, ['g1']);
      composable.confirmIgnoreAllFiat();
      await extractAndCallConfirmCallback();

      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.modelSelectedUnmatched)).toEqual([]);
    });

    it('should reset ignoreLoading on error', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: true, identifier: 1 }),
      ]);
      spies.matchAssetMovements.mockRejectedValueOnce(new Error('fail'));

      const composable = setupWithoutCallback();
      composable.confirmIgnoreAllFiat();

      await expect(extractAndCallConfirmCallback()).rejects.toThrow('fail');
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should still refresh and clear selection when no fiat movements exist', async () => {
      set(unmatchedMovementsRef, [
        createMockMovement({ isFiat: false, identifier: 1 }),
      ]);

      const composable = setupWithoutCallback();
      set(composable.modelSelectedUnmatched, ['g1']);
      composable.confirmIgnoreAllFiat();
      await extractAndCallConfirmCallback();

      expect(spies.matchAssetMovements).not.toHaveBeenCalled();
      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(get(composable.modelSelectedUnmatched)).toEqual([]);
    });
  });

  describe('markExternal', () => {
    it('should resolve the movement as external and report it with an undo', async () => {
      const { composable, onActionComplete } = setupWithCallback();
      const movement = createMockMovement({ identifier: 7 });

      await composable.markExternal(movement);

      expect(spies.resolveExternal).toHaveBeenCalledWith(7);
      expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
      expect(onActionComplete).toHaveBeenCalledOnce();
      expect(get(composable.resolutionNotice)?.movement).toBe(movement);
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should word the notice by direction, so a deposit does not read as a payment out', async () => {
      const composable = setupWithoutCallback();

      await composable.markExternal(createMockMovement({ eventSubtype: 'spend' }));
      const withdrawalMessage = get(composable.resolutionNotice)?.message;

      await composable.markExternal(createMockMovement({ eventSubtype: 'receive', groupIdentifier: 'g2' }));

      expect(get(composable.resolutionNotice)?.message).not.toBe(withdrawalMessage);
    });

    it('should not report a resolution the backend rejected', async () => {
      spies.resolveExternal.mockResolvedValueOnce({ message: 'nope', success: false });
      const { composable, onActionComplete } = setupWithCallback();

      await composable.markExternal(createMockMovement());

      expect(get(composable.resolutionNotice)).toBeUndefined();
      expect(spies.refreshUnmatchedAssetMovements).not.toHaveBeenCalled();
      expect(onActionComplete).not.toHaveBeenCalled();
    });

    it('should clear the loading flag when the resolution throws', async () => {
      spies.resolveExternal.mockRejectedValueOnce(new Error('boom'));
      const composable = setupWithoutCallback();

      await expect(composable.markExternal(createMockMovement())).rejects.toThrow('boom');

      expect(get(composable.ignoreLoading)).toBe(false);
    });
  });

  describe('resolution notice', () => {
    it('should restore the resolved movement when the notice is undone', async () => {
      const composable = setupWithoutCallback();
      await composable.markExternal(createMockMovement({ identifier: 7 }));

      await composable.undoResolution();

      expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(7);
      expect(get(composable.resolutionNotice)).toBeUndefined();
    });

    it('should do nothing when undone with no notice held', async () => {
      const composable = setupWithoutCallback();

      await composable.undoResolution();

      expect(spies.unlinkAssetMovement).not.toHaveBeenCalled();
    });

    it('should drop the notice when the resolved movement is restored from its own row', async () => {
      const composable = setupWithoutCallback();
      const movement = createMockMovement({ groupIdentifier: 'g1' });
      await composable.markExternal(movement);

      await composable.restoreMovement(movement);

      expect(get(composable.resolutionNotice)).toBeUndefined();
    });

    it('should keep the notice when a different movement is restored', async () => {
      const composable = setupWithoutCallback();
      await composable.markExternal(createMockMovement({ groupIdentifier: 'g1' }));

      await composable.restoreMovement(createMockMovement({ groupIdentifier: 'g2', identifier: 2 }));

      expect(get(composable.resolutionNotice)).toBeDefined();
    });

    it('should drop the notice when dismissed', async () => {
      const composable = setupWithoutCallback();
      await composable.markExternal(createMockMovement());

      composable.dismissResolution();

      expect(get(composable.resolutionNotice)).toBeUndefined();
    });
  });

  describe('confirmIgnoreAllFiat batch loading', () => {
    it('should set ignoreLoading during batch operation', async () => {
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
