import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { usePinnedHighlightNavigation } from '@/modules/shell/pinned/use-pinned-highlight-navigation';

const mockRouterReplace = vi.fn().mockResolvedValue(undefined);
const routeQuery = ref<Record<string, unknown>>({});

const { useRouteMock, useRouterMock } = vi.hoisted(() => ({
  useRouteMock: vi.fn(),
  useRouterMock: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: useRouteMock,
  useRouter: useRouterMock,
}));

const clearAllHighlightTargets = vi.fn();
const highlightTargets = ref<Record<string, unknown>>({});

vi.mock('@/modules/history/events/use-history-event-navigation', () => ({
  useHistoryEventNavigation: (): Record<string, unknown> => ({ clearAllHighlightTargets, highlightTargets }),
}));

interface Harness {
  wrapper: VueWrapper;
  clearHighlight: () => Promise<void>;
}

function mountComposable(queryKeys: string[], reset: () => void, isStillPinned?: () => boolean): Harness {
  let clearHighlight!: () => Promise<void>;
  const Comp = defineComponent({
    setup(): () => null {
      ({ clearHighlight } = usePinnedHighlightNavigation(queryKeys, reset, isStillPinned));
      return (): null => null;
    },
  });
  const wrapper = mount(Comp);
  return { clearHighlight, wrapper };
}

describe('usePinnedHighlightNavigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(routeQuery, {});
    set(highlightTargets, {});
    useRouteMock.mockReturnValue(computed(() => ({ query: get(routeQuery) })));
    useRouterMock.mockReturnValue({ replace: mockRouterReplace });
  });

  it('should reset local state, clear shared targets and strip owned query keys', async () => {
    set(routeQuery, { foo: 'bar', highlightedAssetMovement: '42', highlightedPotentialMatch: '7' });
    const reset = vi.fn();
    const { clearHighlight } = mountComposable(['highlightedAssetMovement', 'highlightedPotentialMatch'], reset);

    await clearHighlight();

    expect(reset).toHaveBeenCalledTimes(1);
    expect(clearAllHighlightTargets).toHaveBeenCalledTimes(1);
    expect(mockRouterReplace).toHaveBeenCalledWith({ query: { foo: 'bar' } });
  });

  it('should not touch the route when none of the owned keys are present', async () => {
    set(routeQuery, { foo: 'bar' });
    const reset = vi.fn();
    const { clearHighlight } = mountComposable(['highlightedInternalTxConflict'], reset);

    await clearHighlight();

    expect(reset).toHaveBeenCalledTimes(1);
    expect(clearAllHighlightTargets).toHaveBeenCalledTimes(1);
    expect(mockRouterReplace).not.toHaveBeenCalled();
  });

  it('should reset local state when the shared targets are emptied elsewhere', async () => {
    const reset = vi.fn();
    mountComposable(['highlightedInternalTxConflict'], reset);

    set(highlightTargets, { internalTxConflict: { groupIdentifier: 'g', identifier: 0 } });
    await nextTick();
    expect(reset).not.toHaveBeenCalled();

    set(highlightTargets, {});
    await nextTick();
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it('should clear the highlight on unmount', async () => {
    set(routeQuery, { highlightedInternalTxConflict: 'g' });
    const reset = vi.fn();
    const { wrapper } = mountComposable(['highlightedInternalTxConflict'], reset);

    wrapper.unmount();
    await nextTick();

    expect(reset).toHaveBeenCalled();
    expect(clearAllHighlightTargets).toHaveBeenCalled();
    expect(mockRouterReplace).toHaveBeenCalledWith({ query: {} });
  });

  it('should clear the highlight when the panel is unpinned without unmounting', async () => {
    set(routeQuery, { highlightedInternalTxConflict: 'g' });
    const pinned = ref<boolean>(true);
    const reset = vi.fn();
    // The component stays mounted (as it does under <KeepAlive> when a backgrounded tab
    // is closed); the unpin alone must trigger the cleanup.
    mountComposable(['highlightedInternalTxConflict'], reset, () => get(pinned));

    set(pinned, false);
    await nextTick();

    expect(clearAllHighlightTargets).toHaveBeenCalledTimes(1);
    expect(mockRouterReplace).toHaveBeenCalledWith({ query: {} });
  });

  it('should keep the highlight while the panel stays pinned (a tab-switch)', async () => {
    set(routeQuery, { highlightedInternalTxConflict: 'g' });
    const pinned = ref<boolean>(true);
    const reset = vi.fn();
    mountComposable(['highlightedInternalTxConflict'], reset, () => get(pinned));

    // Toggling other reactive state must not clear while the panel is still pinned.
    set(highlightTargets, { internalTxConflict: {} });
    await nextTick();

    expect(mockRouterReplace).not.toHaveBeenCalled();
  });
});
