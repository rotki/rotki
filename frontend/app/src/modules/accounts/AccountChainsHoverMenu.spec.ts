import type { AccountChainState } from '@/modules/accounts/AccountChainsOverflow.vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { h } from 'vue';
import AccountChainsHoverMenu from '@/modules/accounts/AccountChainsHoverMenu.vue';

const { menuHover, menuLeave } = vi.hoisted(() => ({
  menuHover: vi.fn<() => void>(),
  menuLeave: vi.fn<() => void>(),
}));

/** Hands out hover handlers the spec can watch, and records where the menu is anchored. */
const RuiMenuStub = {
  name: 'RuiMenu',
  emits: ['update:modelValue'],
  props: ['modelValue', 'anchorEl'],
  setup(): { handlers: { onMouseover: () => void; onMouseleave: () => void } } {
    return { handlers: { onMouseleave: menuLeave, onMouseover: menuHover } };
  },
  template: '<div><slot name="activator" :attrs="handlers" /><slot /></div>',
};

const ITEMS: AccountChainState[] = [
  { chain: 'eth', detected: false, enabled: true, skipped: false },
  { chain: 'optimism', detected: false, enabled: true, skipped: false },
];

/** Stands in for the row's icons: each points at the menu when the pointer enters it. */
const IconsStub = {
  props: ['point'],
  template: `<div>
    <span data-chain="eth" @mouseenter="point('eth', $event.currentTarget)" />
    <span data-chain="optimism" @mouseenter="point('optimism', $event.currentTarget)" />
  </div>`,
};

describe('modules/accounts/AccountChainsHoverMenu', () => {
  let wrapper: VueWrapper;

  function createWrapper(open = false): VueWrapper {
    return mount(AccountChainsHoverMenu, {
      global: {
        stubs: {
          AccountSkipQueriesToggle: { props: ['chains'], template: '<div data-testid="skip-toggle" :data-chains="chains.join()" />' },
          I18nT: { props: ['keypath'], template: '<span>{{ keypath }}</span>' },
          RuiMenu: RuiMenuStub,
        },
      },
      props: { filterable: true, items: ITEMS, open, skipAddress: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c' },
      slots: {
        default: (props: { point: (chain: string, element: HTMLElement) => void }) => h(IconsStub, { point: props.point }),
      },
    });
  }

  async function pointAt(chain: string): Promise<void> {
    await wrapper.find(`[data-chain=${chain}]`).trigger('mouseenter');
  }

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should open only once the pointer has rested on an icon', async () => {
    wrapper = createWrapper();

    await pointAt('eth');
    vi.advanceTimersByTime(299);
    expect(menuHover).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(menuHover).toHaveBeenCalledOnce();
  });

  it('should not open for a pointer that only crossed the icons', async () => {
    wrapper = createWrapper();

    await pointAt('eth');
    await wrapper.find('[data-testid=account-chain-icons]').trigger('mouseleave');
    vi.advanceTimersByTime(1000);

    expect(menuHover).not.toHaveBeenCalled();
    expect(menuLeave).toHaveBeenCalledOnce();
  });

  it('should follow the pointer at once while open, anchored to the icon under it', async () => {
    wrapper = createWrapper(true);

    await pointAt('optimism');

    expect(menuHover).toHaveBeenCalledOnce();
    expect(wrapper.findComponent({ name: 'RuiMenu' }).props('anchorEl')).toBe(wrapper.find('[data-chain=optimism]').element);
    expect(wrapper.find('[data-testid=skip-toggle]').attributes('data-chains')).toBe('optimism');
  });

  it('should describe nothing until the pointer reaches an icon', () => {
    wrapper = createWrapper(true);

    expect(wrapper.find('[data-testid=account-chain-menu]').exists()).toBe(false);
  });
});
