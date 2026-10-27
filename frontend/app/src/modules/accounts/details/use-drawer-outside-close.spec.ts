import { mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref } from 'vue';
import { DRAWER_OPENER_ATTRIBUTE, useDrawerOutsideClose } from '@/modules/accounts/details/use-drawer-outside-close';

interface Harness {
  close: ReturnType<typeof vi.fn<() => void>>;
  open: ReturnType<typeof ref<boolean>>;
  click: (testId: string) => void;
}

/** The app root holds the page and an opener; the drawer and a menu are teleported next to it, as in the app. */
function mountDrawer(): Harness {
  const app = document.createElement('div');
  app.id = 'app';
  document.body.append(app);
  const menu = document.createElement('div');
  menu.dataset.testid = 'menu-item';
  document.body.append(menu);

  const close = vi.fn<() => void>();
  const open = ref<boolean>(true);
  const drawer = ref<HTMLElement>();
  const host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      useDrawerOutsideClose({ close, open, target: drawer });
      return () => h('div', [
        h('button', { 'data-testid': 'page' }),
        h('button', { 'data-testid': 'opener', [DRAWER_OPENER_ATTRIBUTE]: '' }, [h('span', { 'data-testid': 'opener-icon' })]),
        h('div', { ref: drawer }, [h('button', { 'data-testid': 'inside' })]),
      ]);
    },
  });
  mount(host, { attachTo: app });

  return {
    click(testId: string): void {
      const target = document.querySelector(`[data-testid=${testId}]`);
      if (!(target instanceof HTMLElement))
        throw new TypeError(`${testId} is missing`);
      target.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
      target.click();
    },
    close,
    open,
  };
}

describe('useDrawerOutsideClose', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('should close on a click on the page', () => {
    const { click, close } = mountDrawer();

    click('page');

    expect(close).toHaveBeenCalledOnce();
  });

  it('should stay open on a click inside it', () => {
    const { click, close } = mountDrawer();

    click('inside');

    expect(close).not.toHaveBeenCalled();
  });

  it('should stay open on a click in a menu or dialog rendered outside the app root', () => {
    const { click, close } = mountDrawer();

    click('menu-item');

    expect(close).not.toHaveBeenCalled();
  });

  it('should stay open on a click on an open button, which switches the account instead', () => {
    const { click, close } = mountDrawer();

    click('opener-icon');

    expect(close).not.toHaveBeenCalled();
  });

  it('should leave clicks alone while closed', () => {
    const { click, close, open } = mountDrawer();
    set(open, false);

    click('page');

    expect(close).not.toHaveBeenCalled();
  });
});
