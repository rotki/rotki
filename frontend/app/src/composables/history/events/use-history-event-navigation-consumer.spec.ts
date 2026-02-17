import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, EffectScope, Ref } from 'vue';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockRouterPush = vi.fn().mockResolvedValue(undefined);
const mockRouterReplace = vi.fn().mockResolvedValue(undefined);
const mockGetHistoryEventGroupPosition = vi.fn();
const mockNotify = vi.fn();

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

vi.mock('@/store/notifications', () => ({
  useNotificationsStore: vi.fn(() => ({
    notify: mockNotify,
  })),
}));

let mockRoute: Ref<{ path: string; query: Record<string, unknown> }>;

function setupMockRoute(path: string = '/history/events', query: Record<string, unknown> = {}): void {
  mockRoute = ref({ path, query });
  useRouteMock.mockReturnValue(mockRoute);
  useRouterMock.mockReturnValue({ currentRoute: mockRoute, push: mockRouterPush, replace: mockRouterReplace });
}

describe('use-history-event-navigation-consumer', () => {
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

  async function importFresh(): Promise<{
    useHistoryEventNavigation: typeof import('./use-history-event-navigation')['useHistoryEventNavigation'];
    useHistoryEventNavigationConsumer: typeof import('./use-history-event-navigation-consumer')['useHistoryEventNavigationConsumer'];
  }> {
    vi.resetModules();
    const [navigation, consumer] = await Promise.all([
      import('./use-history-event-navigation'),
      import('./use-history-event-navigation-consumer'),
    ]);
    return {
      useHistoryEventNavigation: navigation.useHistoryEventNavigation,
      useHistoryEventNavigationConsumer: consumer.useHistoryEventNavigationConsumer,
    };
  }

  function createPagination(limit: number = 10): ComputedRef<TablePaginationData> {
    return computed<TablePaginationData>(() => ({
      limit,
      page: 1,
      total: 100,
    }));
  }

  describe('composable-based navigation', () => {
    it('should resolve position, calculate page, and navigate with asset movement highlight', async () => {
      mockGetHistoryEventGroupPosition.mockResolvedValue(25);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        const { requestNavigation } = useHistoryEventNavigation();

        requestNavigation({
          highlightedAssetMovement: 100,
          targetGroupIdentifier: 'group-1',
        });
      });

      await flushPromises();

      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-1', undefined);
      expect(mockRouterPush).toHaveBeenCalledWith({
        force: true,
        path: '/history/events',
        query: {
          highlightedAssetMovement: '100',
          limit: '10',
          page: '3',
        },
      });
    });

    it('should navigate with potential match highlight', async () => {
      mockGetHistoryEventGroupPosition.mockResolvedValue(0);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        const { requestNavigation } = useHistoryEventNavigation();

        requestNavigation({
          highlightedPotentialMatch: 200,
          targetGroupIdentifier: 'group-2',
        });
      });

      await flushPromises();

      expect(mockRouterPush).toHaveBeenCalledWith({
        force: true,
        path: '/history/events',
        query: {
          highlightedPotentialMatch: '200',
          limit: '10',
          page: '1',
        },
      });
    });

    it('should navigate with negative balance highlight', async () => {
      mockGetHistoryEventGroupPosition.mockResolvedValue(15);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        const { requestNavigation } = useHistoryEventNavigation();

        requestNavigation({
          highlightedNegativeBalanceEvent: 300,
          targetGroupIdentifier: 'group-3',
        });
      });

      await flushPromises();

      expect(mockRouterPush).toHaveBeenCalledWith({
        force: true,
        path: '/history/events',
        query: {
          highlightedNegativeBalanceEvent: '300',
          limit: '10',
          page: '2',
        },
      });
    });

    it('should navigate with multiple highlight types', async () => {
      mockGetHistoryEventGroupPosition.mockResolvedValue(5);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        const { requestNavigation } = useHistoryEventNavigation();

        requestNavigation({
          highlightedAssetMovement: 100,
          highlightedPotentialMatch: 200,
          targetGroupIdentifier: 'group-4',
        });
      });

      await flushPromises();

      expect(mockRouterPush).toHaveBeenCalledWith({
        force: true,
        path: '/history/events',
        query: {
          highlightedAssetMovement: '100',
          highlightedPotentialMatch: '200',
          limit: '10',
          page: '1',
        },
      });
    });

    it('should navigate with only targetGroupIdentifier (no highlights)', async () => {
      mockGetHistoryEventGroupPosition.mockResolvedValue(0);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        const { requestNavigation } = useHistoryEventNavigation();

        requestNavigation({ targetGroupIdentifier: 'group-5' });
      });

      await flushPromises();

      expect(mockRouterPush).toHaveBeenCalledWith({
        force: true,
        path: '/history/events',
        query: {
          limit: '10',
          page: '1',
        },
      });
    });

    it('should calculate page correctly based on pagination limit', async () => {
      mockGetHistoryEventGroupPosition.mockResolvedValue(49);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(25);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        const { requestNavigation } = useHistoryEventNavigation();

        requestNavigation({ targetGroupIdentifier: 'group-6' });
      });

      await flushPromises();

      expect(mockRouterPush).toHaveBeenCalledWith(
        expect.objectContaining({
          query: expect.objectContaining({
            limit: '25',
            page: '2',
          }),
        }),
      );
    });

    it('should call consumeNavigation after successful navigation', async () => {
      mockGetHistoryEventGroupPosition.mockResolvedValue(0);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      const composable = scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        return useHistoryEventNavigation();
      })!;

      composable.requestNavigation({ targetGroupIdentifier: 'group-1' });
      expect(get(composable.isNavigating)).toBe(true);

      await flushPromises();

      expect(get(composable.isNavigating)).toBe(false);
      expect(get(composable.pendingNavigation)).toBeUndefined();
    });

    it('should notify and consume on API error', async () => {
      mockGetHistoryEventGroupPosition.mockRejectedValue(new Error('API failure'));

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      const composable = scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        return useHistoryEventNavigation();
      })!;

      composable.requestNavigation({ targetGroupIdentifier: 'group-bad' });
      await flushPromises();

      expect(mockNotify).toHaveBeenCalledWith({
        display: true,
        message: 'API failure',
        title: expect.any(String),
      });
      expect(get(composable.isNavigating)).toBe(false);
      expect(get(composable.pendingNavigation)).toBeUndefined();
    });

    it('should discard stale request after API returns', async () => {
      let resolveFirst: (value: number) => void;
      const firstPromise = new Promise<number>((resolve) => {
        resolveFirst = resolve;
      });
      mockGetHistoryEventGroupPosition.mockReturnValueOnce(firstPromise);
      mockGetHistoryEventGroupPosition.mockResolvedValueOnce(0);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      const composable = scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        return useHistoryEventNavigation();
      })!;

      // First request (will be slow)
      composable.requestNavigation({ targetGroupIdentifier: 'group-slow' });
      await nextTick();

      // Second request supersedes the first
      composable.requestNavigation({ targetGroupIdentifier: 'group-fast' });
      await flushPromises();

      // Now resolve the first request
      resolveFirst!(5);
      await flushPromises();

      // The router.push from the first request should have been skipped
      // Only the second request's navigation should have completed
      const pushCalls = mockRouterPush.mock.calls.filter(
        (call: any[]) => call[0].force === true,
      );
      expect(pushCalls).toHaveLength(1);
      expect(pushCalls[0][0].query).toEqual(
        expect.objectContaining({ page: '1' }),
      );
    });

    it('should skip processing when pendingNavigation is undefined', async () => {
      const { useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
      });

      await flushPromises();

      expect(mockGetHistoryEventGroupPosition).not.toHaveBeenCalled();
      expect(mockRouterPush).not.toHaveBeenCalled();
    });

    it('should try fallback when position is -1', async () => {
      // First call returns -1 (not found), second call returns position 5
      mockGetHistoryEventGroupPosition.mockResolvedValueOnce(-1);
      mockGetHistoryEventGroupPosition.mockResolvedValueOnce(5);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        const { requestNavigation } = useHistoryEventNavigation();

        requestNavigation({
          fallbacks: [{
            highlightedAssetMovement: 100,
            targetGroupIdentifier: 'group-fallback',
          }],
          highlightedPotentialMatch: 200,
          targetGroupIdentifier: 'group-primary',
        });
      });

      await flushPromises();

      // Should have tried both groups
      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledTimes(2);
      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-primary', undefined);
      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-fallback', undefined);

      // Should navigate to the fallback
      expect(mockRouterPush).toHaveBeenCalledWith({
        force: true,
        path: '/history/events',
        query: {
          highlightedAssetMovement: '100',
          limit: '10',
          page: '1',
        },
      });
    });

    it('should clear highlights when position is -1 and no fallbacks remain', async () => {
      setupMockRoute('/history/events', {
        highlightedAssetMovement: '100',
      });
      mockGetHistoryEventGroupPosition.mockResolvedValue(-1);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        const { requestNavigation } = useHistoryEventNavigation();

        requestNavigation({
          highlightedAssetMovement: 100,
          targetGroupIdentifier: 'group-not-found',
        });
      });

      await flushPromises();

      // Should clear highlights from route
      expect(mockRouterReplace).toHaveBeenCalled();
    });

    it('should not notify on error when preserveFilters is true', async () => {
      mockGetHistoryEventGroupPosition.mockRejectedValue(new Error('API failure'));

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      const composable = scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
        return useHistoryEventNavigation();
      })!;

      composable.requestNavigation({
        highlightedAssetMovement: 100,
        preserveFilters: true,
        targetGroupIdentifier: 'group-filtered',
      });
      await flushPromises();

      // Should NOT notify when preserveFilters is true
      expect(mockNotify).not.toHaveBeenCalled();
      expect(get(composable.isNavigating)).toBe(false);
    });

    it('should preserve route query when preserveFilters is true', async () => {
      setupMockRoute('/history/events', {
        eventTypes: 'deposit',
        limit: '25',
        page: '2',
      });
      mockGetHistoryEventGroupPosition.mockResolvedValue(30);

      const { useHistoryEventNavigation, useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(25);
      const loading = ref<boolean>(false);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination, undefined, loading);
        const { requestNavigation } = useHistoryEventNavigation();

        requestNavigation({
          highlightedAssetMovement: 100,
          preserveFilters: true,
          targetGroupIdentifier: 'group-filtered',
        });
      });

      // Simulate pagination system loading cycle
      set(loading, true);
      await nextTick();
      set(loading, false);
      await flushPromises();

      // Should merge page + highlights into existing route while preserving filter params
      expect(mockRouterPush).toHaveBeenCalledWith({
        force: true,
        path: '/history/events',
        query: expect.objectContaining({
          eventTypes: 'deposit',
          highlightedAssetMovement: '100',
          limit: '25',
          page: '2',
        }),
      });
    });
  });

  describe('route-based navigation', () => {
    it('should trigger navigation from route query params', async () => {
      setupMockRoute('/history/events', {
        targetGroupIdentifier: 'group-route',
        highlightedNegativeBalanceEvent: '500',
      });
      mockGetHistoryEventGroupPosition.mockResolvedValue(10);

      const { useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
      });

      await flushPromises();

      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-route', undefined);
      expect(mockRouterPush).toHaveBeenCalledWith({
        force: true,
        path: '/history/events',
        query: {
          highlightedNegativeBalanceEvent: '500',
          limit: '10',
          page: '2',
        },
      });
    });

    it('should not trigger navigation when targetGroupIdentifier is missing', async () => {
      setupMockRoute('/history/events', {
        highlightedNegativeBalanceEvent: '500',
      });

      const { useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
      });

      await flushPromises();

      expect(mockGetHistoryEventGroupPosition).not.toHaveBeenCalled();
    });

    it('should not trigger navigation when highlightedNegativeBalanceEvent is missing', async () => {
      setupMockRoute('/history/events', {
        targetGroupIdentifier: 'group-1',
      });

      const { useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
      });

      await flushPromises();

      expect(mockGetHistoryEventGroupPosition).not.toHaveBeenCalled();
    });

    it('should react to route changes with new navigation params', async () => {
      setupMockRoute('/history/events');
      mockGetHistoryEventGroupPosition.mockResolvedValue(0);

      const { useHistoryEventNavigationConsumer } = await importFresh();
      const pagination = createPagination(10);

      scope.run(() => {
        useHistoryEventNavigationConsumer(pagination);
      });

      await flushPromises();
      expect(mockGetHistoryEventGroupPosition).not.toHaveBeenCalled();

      // Simulate route change with navigation params
      set(mockRoute, {
        path: '/history/events',
        query: {
          targetGroupIdentifier: 'group-new',
          highlightedNegativeBalanceEvent: '999',
        },
      });

      await flushPromises();

      expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-new', undefined);
    });
  });
});
