import type { EffectScope } from 'vue';
import type { HistoryEventNavigationRequest } from './use-history-event-navigation';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockRouterPush = vi.fn().mockResolvedValue(undefined);
const mockGetHistoryEventGroupPosition = vi.fn();

const { useRouteMock, useRouterMock } = vi.hoisted(() => ({
  useRouteMock: vi.fn(),
  useRouterMock: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: useRouteMock,
  useRouter: useRouterMock,
}));

vi.mock('@/composables/api/history/events', () => ({
  useHistoryEventsApi: vi.fn(() => ({
    getHistoryEventGroupPosition: mockGetHistoryEventGroupPosition,
  })),
}));

function setupMockRoute(path: string = '/history/events', query: Record<string, unknown> = {}): void {
  const mockRoute = ref<{ path: string; query: Record<string, unknown> }>({ path, query });
  useRouteMock.mockReturnValue(mockRoute);
  useRouterMock.mockReturnValue({ currentRoute: mockRoute, push: mockRouterPush });
}

describe('use-history-event-navigation', () => {
  let scope: EffectScope;

  beforeEach(() => {
    scope = effectScope();
    setupMockRoute();
    vi.clearAllMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
  });

  // Re-import for each test to reset the module-level shared composable state
  async function importFresh(): Promise<typeof import('./use-history-event-navigation')> {
    vi.resetModules();
    return import('./use-history-event-navigation');
  }

  it('should set pendingNavigation and isNavigating on requestNavigation', async () => {
    const { useHistoryEventNavigation } = await importFresh();
    const { isNavigating, pendingNavigation, requestNavigation } = scope.run(() => useHistoryEventNavigation())!;

    const request: HistoryEventNavigationRequest = {
      targetGroupIdentifier: 'group-1',
      highlightedAssetMovement: 42,
    };

    requestNavigation(request);

    expect(get(isNavigating)).toBe(true);
    expect(get(pendingNavigation)).toEqual(request);
  });

  it('should clear pendingNavigation and isNavigating on consumeNavigation', async () => {
    const { useHistoryEventNavigation } = await importFresh();
    const { consumeNavigation, isNavigating, pendingNavigation, requestNavigation } = scope.run(() => useHistoryEventNavigation())!;

    requestNavigation({ targetGroupIdentifier: 'group-1' });
    expect(get(isNavigating)).toBe(true);
    expect(get(pendingNavigation)).toBeTruthy();

    consumeNavigation();

    expect(get(isNavigating)).toBe(false);
    expect(get(pendingNavigation)).toBeUndefined();
  });

  it('should navigate to history events route when not already on it', async () => {
    setupMockRoute('/dashboard');
    const { useHistoryEventNavigation } = await importFresh();
    const { requestNavigation } = scope.run(() => useHistoryEventNavigation())!;

    requestNavigation({ targetGroupIdentifier: 'group-1' });

    expect(mockRouterPush).toHaveBeenCalledWith({ path: '/history/events' });
  });

  it('should not navigate when already on history events route', async () => {
    setupMockRoute('/history/events');
    const { useHistoryEventNavigation } = await importFresh();
    const { requestNavigation } = scope.run(() => useHistoryEventNavigation())!;

    requestNavigation({ targetGroupIdentifier: 'group-1' });

    expect(mockRouterPush).not.toHaveBeenCalled();
  });

  it('should not navigate when on a sub-path of history events', async () => {
    setupMockRoute('/history/events?page=2');
    const { useHistoryEventNavigation } = await importFresh();
    const { requestNavigation } = scope.run(() => useHistoryEventNavigation())!;

    requestNavigation({ targetGroupIdentifier: 'group-1' });

    expect(mockRouterPush).not.toHaveBeenCalled();
  });

  it('should set and clear highlight targets', async () => {
    const { useHistoryEventNavigation } = await importFresh();
    const { clearAllHighlightTargets, clearHighlightTarget, highlightTargets, setHighlightTarget } = scope.run(() => useHistoryEventNavigation())!;

    setHighlightTarget('assetMovement', { groupIdentifier: 'group-1', identifier: 100 });
    setHighlightTarget('potentialMatch', { groupIdentifier: 'group-2', identifier: 200 });

    expect(get(highlightTargets)).toEqual({
      assetMovement: { groupIdentifier: 'group-1', identifier: 100 },
      potentialMatch: { groupIdentifier: 'group-2', identifier: 200 },
    });

    clearHighlightTarget('potentialMatch');
    expect(get(highlightTargets)).toEqual({
      assetMovement: { groupIdentifier: 'group-1', identifier: 100 },
    });

    clearAllHighlightTargets();
    expect(get(highlightTargets)).toEqual({});
  });

  describe('findHighlightPage', () => {
    it('should return correct page when event is found', async () => {
      mockGetHistoryEventGroupPosition.mockResolvedValue(25);

      const { useHistoryEventNavigation } = await importFresh();
      const { findHighlightPage, setHighlightTarget } = scope.run(() => useHistoryEventNavigation())!;

      setHighlightTarget('assetMovement', { groupIdentifier: 'group-1', identifier: 100 });

      const page = await findHighlightPage({} as any, 10);
      expect(page).toBe(3); // position 25, limit 10 → page 3
      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-1', {});
    });

    it('should return -1 when no highlights are active', async () => {
      const { useHistoryEventNavigation } = await importFresh();
      const { findHighlightPage } = scope.run(() => useHistoryEventNavigation())!;

      const page = await findHighlightPage({} as any, 10);
      expect(page).toBe(-1);
      expect(mockGetHistoryEventGroupPosition).not.toHaveBeenCalled();
    });

    it('should try candidates in priority order (green > yellow > red)', async () => {
      // Green found at position 5
      mockGetHistoryEventGroupPosition.mockResolvedValueOnce(5);

      const { useHistoryEventNavigation } = await importFresh();
      const { findHighlightPage, setHighlightTarget } = scope.run(() => useHistoryEventNavigation())!;

      setHighlightTarget('potentialMatch', { groupIdentifier: 'group-green', identifier: 200 });
      setHighlightTarget('assetMovement', { groupIdentifier: 'group-yellow', identifier: 100 });
      setHighlightTarget('negativeBalance', { groupIdentifier: 'group-red', identifier: 300 });

      const page = await findHighlightPage({} as any, 10);
      expect(page).toBe(1); // position 5, limit 10 → page 1

      // Only the green candidate should have been checked (found immediately)
      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledTimes(1);
      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-green', {});
    });

    it('should fall back to next candidate when position is -1', async () => {
      // Green not found, yellow found at position 15
      mockGetHistoryEventGroupPosition.mockResolvedValueOnce(-1);
      mockGetHistoryEventGroupPosition.mockResolvedValueOnce(15);

      const { useHistoryEventNavigation } = await importFresh();
      const { findHighlightPage, setHighlightTarget } = scope.run(() => useHistoryEventNavigation())!;

      setHighlightTarget('potentialMatch', { groupIdentifier: 'group-green', identifier: 200 });
      setHighlightTarget('assetMovement', { groupIdentifier: 'group-yellow', identifier: 100 });

      const page = await findHighlightPage({} as any, 10);
      expect(page).toBe(2); // position 15, limit 10 → page 2
      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledTimes(2);
    });

    it('should return -1 when all candidates fail', async () => {
      mockGetHistoryEventGroupPosition.mockResolvedValue(-1);

      const { useHistoryEventNavigation } = await importFresh();
      const { findHighlightPage, setHighlightTarget } = scope.run(() => useHistoryEventNavigation())!;

      setHighlightTarget('assetMovement', { groupIdentifier: 'group-1', identifier: 100 });

      const page = await findHighlightPage({} as any, 10);
      expect(page).toBe(-1);
    });

    it('should return -1 when API throws error', async () => {
      mockGetHistoryEventGroupPosition.mockRejectedValue(new Error('API error'));

      const { useHistoryEventNavigation } = await importFresh();
      const { findHighlightPage, setHighlightTarget } = scope.run(() => useHistoryEventNavigation())!;

      setHighlightTarget('assetMovement', { groupIdentifier: 'group-1', identifier: 100 });

      const page = await findHighlightPage({} as any, 10);
      expect(page).toBe(-1);
    });
  });
});
