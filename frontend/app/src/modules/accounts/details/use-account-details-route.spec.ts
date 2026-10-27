import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountDetailsRoute } from '@/modules/accounts/details/use-account-details-route';

type Query = Record<string, string | string[]>;

interface RouteHolder {
  route?: { value: { query: Query } };
  /** vue-router's position of the current history entry: a push moves it on, a replace keeps it. */
  position: number;
}

/**
 * The global `vue-router` mock has no `replace`, `back` or history state and returns a plain object,
 * so the spec keeps its own route ref and history position and lets push/replace move them the way
 * the router would.
 */
const { back, held, push, replace } = vi.hoisted(() => {
  const held: RouteHolder = { position: 0 };
  const write = async ({ query }: { query: Query }): Promise<void> => {
    assert(held.route);
    held.route.value = { query };
  };
  return {
    back: vi.fn<() => void>(),
    held,
    push: vi.fn(async (location: { query: Query }): Promise<void> => {
      held.position++;
      await write(location);
    }),
    replace: vi.fn(write),
  };
});

vi.mock('vue-router', async () => {
  const { ref } = await vi.importActual<typeof import('vue')>('vue');
  held.route = ref({ query: {} });
  return {
    useRoute: (): unknown => held.route,
    useRouter: (): Record<string, unknown> => ({
      back,
      options: { history: { get state(): Record<string, unknown> { return { position: held.position }; } } },
      push,
      replace,
    }),
  };
});

function setQuery(query: Query): void {
  assert(held.route);
  held.route.value = { query };
}

describe('useAccountDetailsRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    held.position = 0;
    setQuery({ limit: '10' });
  });

  it('should read the open account and tab from the query', () => {
    setQuery({ account: '0xabc', view: 'chains' });
    const { accountId, view } = useAccountDetailsRoute();

    expect(get(accountId)).toBe('0xabc');
    expect(get(view)).toBe('chains');
  });

  it('should ignore a tab the drawer does not have', () => {
    setQuery({ account: '0xabc', view: 'positions' });

    expect(get(useAccountDetailsRoute().view)).toBeUndefined();
  });

  it('should push a history entry when asked to, keeping the table query', async () => {
    const { open } = useAccountDetailsRoute();

    await open('0xabc', 'push');

    expect(push).toHaveBeenCalledWith({ query: { account: '0xabc', limit: '10' } });
    expect(replace).not.toHaveBeenCalled();
  });

  it('should rewrite the entry when switching accounts, dropping the old tab', async () => {
    setQuery({ account: '0xabc', limit: '10', view: 'chains' });
    const { open } = useAccountDetailsRoute();

    await open('0xdef', 'replace');

    expect(replace).toHaveBeenCalledWith({ query: { account: '0xdef', limit: '10' } });
    expect(push).not.toHaveBeenCalled();
  });

  it('should go back on close while the current entry is the one it pushed', async () => {
    const { close, open } = useAccountDetailsRoute();
    await open('0xabc', 'push');

    await close();

    expect(back).toHaveBeenCalledOnce();
    expect(replace).not.toHaveBeenCalled();
  });

  it('should drop its keys instead of going back once a table write pushed another entry on top', async () => {
    const { close, open } = useAccountDetailsRoute();
    await open('0xabc', 'push');
    await push({ query: { account: '0xabc', limit: '25' } });
    push.mockClear();

    await close();

    expect(back).not.toHaveBeenCalled();
    expect(replace).toHaveBeenCalledWith({ query: { limit: '25' } });
  });

  it('should drop both of its keys on discard', async () => {
    setQuery({ account: '0xgone', limit: '10', view: 'chains' });

    await useAccountDetailsRoute().discard();

    expect(replace).toHaveBeenCalledWith({ query: { limit: '10' } });
  });

  it('should only drop its keys on close when the drawer arrived open', async () => {
    setQuery({ account: '0xabc', limit: '10', view: 'chains' });
    const { close } = useAccountDetailsRoute();

    await close();

    expect(back).not.toHaveBeenCalled();
    expect(replace).toHaveBeenCalledWith({ query: { limit: '10' } });
  });

  it('should drop its keys on close after Back already closed what it pushed', async () => {
    const { close, open } = useAccountDetailsRoute();
    await open('0xabc', 'push');
    setQuery({ limit: '10' });
    await nextTick();
    setQuery({ account: '0xdef', limit: '10' });

    await close();

    expect(back).not.toHaveBeenCalled();
    expect(replace).toHaveBeenCalledWith({ query: { limit: '10' } });
  });

  it('should replace the entry when switching tabs', async () => {
    setQuery({ account: '0xabc' });
    const { setView } = useAccountDetailsRoute();

    await setView('chains');

    expect(replace).toHaveBeenCalledWith({ query: { account: '0xabc', view: 'chains' } });
    expect(push).not.toHaveBeenCalled();
  });
});
