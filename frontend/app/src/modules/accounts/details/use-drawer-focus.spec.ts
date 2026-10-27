import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref } from 'vue';
import { useDrawerFocus } from '@/modules/accounts/details/use-drawer-focus';

interface FocusHarness {
  open: ReturnType<typeof ref<boolean>>;
  opener: HTMLButtonElement;
  inside: HTMLButtonElement;
  outside: HTMLInputElement;
}

function element<T extends Element>(root: Element, selector: string, type: new () => T): T {
  const found = root.querySelector(selector);
  if (!(found instanceof type))
    throw new TypeError(`${selector} is missing`);
  return found;
}

function mountWithFocus(focusInside: () => void): FocusHarness {
  const open = ref<boolean>(false);
  const drawer = ref<HTMLElement>();
  const host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      useDrawerFocus(open, focusInside, drawer);
      return () => h('div', [
        h('button', { 'data-testid': 'opener' }, 'open'),
        h('input', { 'data-testid': 'outside' }),
        h('div', { ref: drawer }, [h('button', { 'data-testid': 'inside' }, 'close')]),
      ]);
    },
  });
  const root = mount(host, { attachTo: document.body }).element;
  return {
    inside: element(root, '[data-testid=inside]', HTMLButtonElement),
    open,
    opener: element(root, '[data-testid=opener]', HTMLButtonElement),
    outside: element(root, '[data-testid=outside]', HTMLInputElement),
  };
}

describe('useDrawerFocus', () => {
  it('should focus inside the drawer when it opens and return focus to the opener when it closes', async () => {
    const focusInside = vi.fn<() => void>(() => {
      if (document.activeElement instanceof HTMLElement)
        document.activeElement.blur();
    });
    const { open, opener } = mountWithFocus(focusInside);
    opener.focus();

    set(open, true);
    await nextTick();
    await nextTick();

    expect(focusInside).toHaveBeenCalledOnce();
    expect(document.activeElement).not.toBe(opener);

    set(open, false);
    await nextTick();

    expect(document.activeElement).toBe(opener);
  });

  it('should leave focus alone on close when the opener left the document', async () => {
    const { open, opener } = mountWithFocus(() => {});
    opener.focus();
    set(open, true);
    await nextTick();
    opener.remove();

    set(open, false);
    await nextTick();

    expect(document.activeElement).not.toBe(opener);
  });

  it('should return focus to the opener when it closes from inside the drawer', async () => {
    const { inside, open, opener } = mountWithFocus(() => {});
    opener.focus();
    set(open, true);
    await nextTick();
    inside.focus();

    set(open, false);
    await nextTick();

    expect(document.activeElement).toBe(opener);
  });

  it('should leave focus where the user put it when a click on the page closed the drawer', async () => {
    const { open, opener, outside } = mountWithFocus(() => {});
    opener.focus();
    set(open, true);
    await nextTick();
    outside.focus();

    set(open, false);
    await nextTick();

    expect(document.activeElement).toBe(outside);
  });
});
