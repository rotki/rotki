import type { useActionCenter as UseActionCenter } from '@/modules/core/action-center/use-action-center';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type ActionItem, ActionSeverity } from '@/modules/core/action-center/types';

const state = {
  logged: ref(true),
};

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ logged: state.logged }),
}));

function createItem(overrides: Partial<ActionItem> = {}): ActionItem {
  return {
    actionLabel: 'act',
    checkTarget: { kind: 'run', run: (): void => {} },
    count: 0,
    description: 'description',
    icon: 'lu-wallet',
    id: 'an-item',
    informational: false,
    loading: false,
    locked: false,
    minimumTier: null,
    severity: ActionSeverity.WARNING,
    target: { kind: 'run', run: (): void => {} },
    title: 'An item',
    ...overrides,
  };
}

/**
 * Imports the composable into a fresh module registry.
 *
 * @remarks
 * Whether a center has scanned is module-level state shared by every consumer, so a plain top-level
 * import would let one test's scan decide the next test's starting point.
 */
async function loadComposable(): Promise<typeof UseActionCenter> {
  vi.resetModules();
  const module = await import('@/modules/core/action-center/use-action-center');
  return module.useActionCenter;
}

describe('modules/core/action-center/useActionCenter', () => {
  let useActionCenter: typeof UseActionCenter;

  beforeEach(async () => {
    vi.clearAllMocks();
    set(state.logged, true);
    useActionCenter = await loadComposable();
  });

  it('should split the items by what they are asking for', () => {
    const items = ref<ActionItem[]>([
      createItem({ count: 2, id: 'active' }),
      createItem({ count: 3, id: 'locked', locked: true }),
      createItem({ count: 4, id: 'review', informational: true }),
      createItem({ count: 0, id: 'cleared' }),
      createItem({ count: 9, id: 'counting', loading: true }),
    ]);

    const { activeItems, categoryCount, clearedItems, hasItems, lockedItems, reviewItems } = useActionCenter({
      id: 'test',
      items,
      sources: [],
    });

    expect(get(activeItems).map(item => item.id)).toEqual(['active']);
    expect(get(lockedItems).map(item => item.id)).toEqual(['locked']);
    expect(get(reviewItems).map(item => item.id)).toEqual(['review']);
    // A loading item counts as cleared until its count lands, rather than raising an untrustworthy row.
    expect(get(clearedItems).map(item => item.id)).toEqual(['cleared', 'counting']);
    expect(get(categoryCount)).toBe(1);
    expect(get(hasItems)).toBe(true);
  });

  it('should stay pending until a scan lands, and while a source is reading', async () => {
    const loading = ref<boolean>(false);
    const refresh = vi.fn<() => Promise<void>>().mockResolvedValue();

    const { checking, refreshAll, refreshing } = useActionCenter({
      id: 'test',
      items: ref([]),
      sources: [{ loading, refresh }],
    });

    expect(get(checking)).toBe(true);

    await refreshAll();

    expect(get(checking)).toBe(false);
    expect(get(refreshing)).toBe(false);

    set(loading, true);

    expect(get(refreshing)).toBe(true);
    expect(get(checking)).toBe(true);
  });

  it('should keep checking while the domain says it is busy', async () => {
    const busy = ref<boolean>(false);
    const { checking, refreshAll } = useActionCenter({
      busy,
      id: 'test',
      items: ref([]),
      sources: [],
    });

    await refreshAll();

    expect(get(checking)).toBe(false);

    set(busy, true);

    expect(get(checking)).toBe(true);
  });

  it('should read every source on a re-scan, and survive one that rejects', async () => {
    const ok = vi.fn<() => Promise<void>>().mockResolvedValue();
    const broken = vi.fn<() => Promise<void>>().mockRejectedValue(new Error('nope'));

    const { checking, refreshAll } = useActionCenter({
      id: 'test',
      items: ref([]),
      sources: [{ refresh: broken }, { refresh: ok }],
    });

    await refreshAll();

    expect(broken).toHaveBeenCalledOnce();
    expect(ok).toHaveBeenCalledOnce();
    // one source failing must not pin the center to "checking" for the session
    expect(get(checking)).toBe(false);
  });

  it('should share the scanned flag between consumers of the same center', async () => {
    const trigger = useActionCenter({ id: 'shared', items: ref([]), sources: [] });
    const panel = useActionCenter({ id: 'shared', items: ref([]), sources: [] });
    const other = useActionCenter({ id: 'elsewhere', items: ref([]), sources: [] });

    await trigger.refreshAll();

    expect(get(panel.checking)).toBe(false);
    expect(get(other.checking)).toBe(true);
  });

  it('should go back to pending for the next user', async () => {
    const { checking, refreshAll } = useActionCenter({ id: 'test', items: ref([]), sources: [] });

    await refreshAll();
    expect(get(checking)).toBe(false);

    set(state.logged, false);
    await nextTick();

    expect(get(checking)).toBe(true);
  });
});
