import type { SearchItem } from '@/modules/shell/layout/use-global-search';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import GlobalSearch from '@/modules/shell/components/GlobalSearch.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { currentPath, isMac, performSearch, push, resolve } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    currentPath: ref<string>('/dashboard'),
    isMac: vi.fn(),
    performSearch: vi.fn(),
    push: vi.fn(),
    resolve: vi.fn(),
  };
});

vi.mock('vue-router', () => ({
  useRouter: (): Record<string, unknown> => ({
    currentRoute: computed(() => ({ fullPath: get(currentPath) })),
    push,
    resolve,
  }),
}));

vi.mock('@/modules/shell/layout/use-global-search', () => ({
  useGlobalSearch: (): { search: Mock } => ({ search: performSearch }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): { isMac: Mock } => ({ isMac }),
}));

/** The shared stub carries neither of this component's two models, so it is replaced here. */
const AutoCompleteStub = {
  emits: ['update:modelValue', 'update:searchInput'],
  name: 'RuiAutoComplete',
  props: ['modelValue', 'searchInput', 'options', 'loading'],
  template: '<div />',
};

const DialogStub = { name: 'RuiDialog', props: ['modelValue'], template: '<div><slot /></div>' };

function item(overrides: Partial<SearchItem> = {}): SearchItem {
  return { matchedPoints: 1, texts: ['Dashboard'], value: 1, ...overrides };
}

function createWrapper(): VueWrapper<any> {
  return mount(GlobalSearch, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        AppImage: true,
        AssetIcon: true,
        FiatDisplay: true,
        GlobalSearchItemTexts: true,
        LocationIcon: true,
        RuiAutoComplete: AutoCompleteStub,
        RuiDialog: DialogStub,
      },
    },
  });
}

function palette(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(DialogStub);
}

function isOpen(wrapper: VueWrapper<any>): boolean {
  return palette(wrapper).props('modelValue');
}

/** Presses the palette shortcut, which is Command on macOS and Control everywhere else. */
async function pressShortcut(modifier: 'meta' | 'ctrl', key = '/'): Promise<void> {
  window.dispatchEvent(new KeyboardEvent('keydown', {
    ctrlKey: modifier === 'ctrl',
    key,
    metaKey: modifier === 'meta',
  }));
  await nextTick();
}

/** Mounts and lets `onBeforeMount` settle, since the platform is resolved asynchronously. */
async function mountReady(): Promise<VueWrapper<any>> {
  const wrapper = createWrapper();
  await flushPromises();
  return wrapper;
}

/** Chooses the item at that index, the way the autocomplete reports a selection. */
async function choose(wrapper: VueWrapper<any>, index: number): Promise<void> {
  await wrapper.findComponent(AutoCompleteStub).vm.$emit('update:modelValue', index);
  await nextTick();
}

describe('globalSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(currentPath, '/dashboard');
    isMac.mockResolvedValue(false);
    performSearch.mockResolvedValue([]);
    push.mockResolvedValue(undefined);
    resolve.mockImplementation((route: string) => ({ fullPath: route }));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /**
   * The modifier check is one way round rather than accepting either, so the wrong modifier does
   * not open the palette on the platform it does not belong to.
   */
  describe('the keyboard shortcut', () => {
    it('should open on control off macOS', async () => {
      const wrapper = await mountReady();

      await pressShortcut('ctrl');

      expect(isOpen(wrapper)).toBe(true);
    });

    it('should ignore command off macOS', async () => {
      const wrapper = await mountReady();

      await pressShortcut('meta');

      expect(isOpen(wrapper)).toBe(false);
    });

    it('should open on command on macOS', async () => {
      isMac.mockResolvedValue(true);
      const wrapper = await mountReady();

      await pressShortcut('meta');

      expect(isOpen(wrapper)).toBe(true);
    });

    it('should ignore control on macOS', async () => {
      isMac.mockResolvedValue(true);
      const wrapper = await mountReady();

      await pressShortcut('ctrl');

      expect(isOpen(wrapper)).toBe(false);
    });

    it('should ignore the modifier on its own', async () => {
      const wrapper = await mountReady();

      await pressShortcut('ctrl', 'k');

      expect(isOpen(wrapper)).toBe(false);
    });
  });

  describe('choosing a result', () => {
    it('should navigate to the route it carries', async () => {
      performSearch.mockResolvedValue([item({ route: '/settings/general' })]);
      const wrapper = await mountReady();
      await search(wrapper, 'settings');

      await choose(wrapper, 0);

      expect(push).toHaveBeenCalledWith('/settings/general');
    });

    /** Pushing the route the user is already on would stack a pointless history entry. */
    it('should not navigate when it leads where the user already is', async () => {
      performSearch.mockResolvedValue([item({ route: '/dashboard' })]);
      const wrapper = await mountReady();
      await search(wrapper, 'dash');

      await choose(wrapper, 0);

      expect(push).not.toHaveBeenCalled();
    });

    it('should run an item that acts instead of navigating', async () => {
      const action = vi.fn();
      performSearch.mockResolvedValue([item({ action })]);
      const wrapper = await mountReady();
      await search(wrapper, 'privacy');

      await choose(wrapper, 0);

      expect(action).toHaveBeenCalledTimes(1);
      expect(push).not.toHaveBeenCalled();
    });

    it('should close the palette', async () => {
      performSearch.mockResolvedValue([item({ route: '/settings/general' })]);
      const wrapper = await mountReady();
      await pressShortcut('ctrl');
      await search(wrapper, 'settings');

      await choose(wrapper, 0);

      expect(isOpen(wrapper)).toBe(false);
    });

    it('should do nothing for an index no result sits at', async () => {
      const wrapper = await mountReady();

      await choose(wrapper, 3);

      expect(push).not.toHaveBeenCalled();
    });
  });

  describe('searching', () => {
    it('should report itself busy as soon as something is typed', async () => {
      const wrapper = await mountReady();

      await wrapper.findComponent(AutoCompleteStub).vm.$emit('update:searchInput', 'set');
      await nextTick();

      expect(wrapper.findComponent(AutoCompleteStub).props('loading')).toBe(true);
    });

    /** The search is debounced, so a keystroke must not reach it until the typing settles. */
    it('should wait for the typing to settle before searching', async () => {
      vi.useFakeTimers();
      const wrapper = createWrapper();
      await vi.advanceTimersByTimeAsync(0);

      await wrapper.findComponent(AutoCompleteStub).vm.$emit('update:searchInput', 'set');
      await vi.advanceTimersByTimeAsync(400);

      expect(performSearch).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(500);

      expect(performSearch).toHaveBeenCalledWith('set');
    });

    it('should offer what came back and stop reporting itself busy', async () => {
      performSearch.mockResolvedValue([item(), item({ value: 2 })]);
      const wrapper = await mountReady();

      await search(wrapper, 'set');

      expect(wrapper.findComponent(AutoCompleteStub).props('options')).toHaveLength(2);
      expect(wrapper.findComponent(AutoCompleteStub).props('loading')).toBe(false);
    });
  });
});

/** Types into the palette and lets the debounce elapse. */
async function search(wrapper: VueWrapper<any>, keyword: string): Promise<void> {
  vi.useFakeTimers();
  await wrapper.findComponent(AutoCompleteStub).vm.$emit('update:searchInput', keyword);
  await vi.advanceTimersByTimeAsync(900);
  vi.useRealTimers();
  await flushPromises();
}
