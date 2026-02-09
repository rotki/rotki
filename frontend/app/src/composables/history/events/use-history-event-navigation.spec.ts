import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, EffectScope, Ref } from 'vue';
import type { HistoryEventNavigationRequest } from './use-history-event-navigation';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockRouterPush = vi.fn().mockResolvedValue(undefined);
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

  describe('useHistoryEventNavigation', () => {
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
  });

  describe('useHistoryEventNavigationConsumer', () => {
    async function importFresh(): Promise<typeof import('./use-history-event-navigation')> {
      vi.resetModules();
      return import('./use-history-event-navigation');
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

        expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-1');
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

        expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-route');
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

        expect(mockGetHistoryEventGroupPosition).toHaveBeenCalledWith('group-new');
      });
    });
  });
});
