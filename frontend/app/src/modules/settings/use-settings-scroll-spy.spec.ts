import { assert } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount } from '@vue/test-utils';
import { get } from '@vueuse/core';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type ShallowRef, shallowRef, type VNode } from 'vue';
import { useSettingsScrollSpy } from '@/modules/settings/use-settings-scroll-spy';

interface ScrollerProps {
  scrollTop?: number;
  clientHeight?: number;
  scrollHeight?: number;
  rect?: DOMRect;
}

const navigation = [
  { id: 'a', label: 'A' },
  { id: 'b', label: 'B' },
  { id: 'c', label: 'C' },
];

function makeEl(x: number, y: number, w: number, h: number): Element {
  return createMock<Element>({ getBoundingClientRect: () => new DOMRect(x, y, w, h) });
}

function makeScroller(props: ScrollerProps = {}): HTMLDivElement {
  const { clientHeight = 100, rect = new DOMRect(0, 0, 100, 100), scrollHeight = 100, scrollTop = 0 } = props;
  const div = document.createElement('div');
  div.getBoundingClientRect = (): DOMRect => rect;
  div.scrollTo = vi.fn();
  div.scrollTop = scrollTop;
  Object.defineProperty(div, 'clientHeight', { configurable: true, value: clientHeight });
  Object.defineProperty(div, 'scrollHeight', { configurable: true, value: scrollHeight });
  return div;
}

function scrollerRef(div: HTMLDivElement | null): ShallowRef<HTMLDivElement | null> {
  return shallowRef<HTMLDivElement | null>(div);
}

function setup(
  scroller: ShallowRef<HTMLDivElement | null>,
): ReturnType<typeof useSettingsScrollSpy> {
  let api: ReturnType<typeof useSettingsScrollSpy> | undefined;
  mount(defineComponent({
    setup(): () => VNode {
      api = useSettingsScrollSpy({ navigation, scroller });
      return () => h('div');
    },
  }));
  assert(api);
  return api;
}

describe('useSettingsScrollSpy', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('isElementInViewport', () => {
    it('should return false without a scroller', () => {
      const { isElementInViewport } = setup(scrollerRef(null));
      expect(isElementInViewport(makeEl(10, 10, 10, 10))).toBe(false);
    });

    it('should return true for an overlapping element', () => {
      const { isElementInViewport } = setup(scrollerRef(makeScroller()));
      expect(isElementInViewport(makeEl(10, 10, 10, 10))).toBe(true);
    });

    it('should return false for an element outside the scroller', () => {
      const { isElementInViewport } = setup(scrollerRef(makeScroller()));
      expect(isElementInViewport(makeEl(200, 200, 10, 10))).toBe(false);
    });
  });

  describe('checkVisibility on mount', () => {
    it('should select the first nav item when scrolled to the top', () => {
      const { currentId } = setup(scrollerRef(makeScroller({ scrollTop: 0 })));
      expect(get(currentId)).toBe('a');
    });

    it('should select the last nav item when scrolled to the bottom', () => {
      const scroller = makeScroller({ clientHeight: 500, scrollHeight: 1500, scrollTop: 1000 });
      const { currentId } = setup(scrollerRef(scroller));
      expect(get(currentId)).toBe('c');
    });

    it('should fall back to the first nav item when no element is in view', () => {
      const scroller = makeScroller({ clientHeight: 100, scrollHeight: 1000, scrollTop: 300 });
      const { currentId } = setup(scrollerRef(scroller));
      expect(get(currentId)).toBe('a');
    });
  });

  describe('scrollToElement', () => {
    it('should resolve immediately without a target', async () => {
      const { scrollToElement } = setup(scrollerRef(makeScroller()));
      await expect(scrollToElement()).resolves.toBeUndefined();
    });

    it('should resolve immediately when already at the target', async () => {
      const scrollTo = vi.fn();
      const scroller = makeScroller({ rect: new DOMRect(0, 0, 100, 100), scrollTop: 0 });
      scroller.scrollTo = scrollTo;
      const { scrollToElement } = setup(scrollerRef(scroller));
      await expect(scrollToElement(makeEl(0, 20, 10, 10))).resolves.toBeUndefined();
      expect(scrollTo).not.toHaveBeenCalled();
    });

    it('should scroll and resolve on scrollend', async () => {
      const scrollTo = vi.fn();
      const scroller = makeScroller({ rect: new DOMRect(0, 0, 100, 100), scrollTop: 100 });
      scroller.scrollTo = scrollTo;
      const { scrollToElement } = setup(scrollerRef(scroller));

      const promise = scrollToElement(makeEl(0, 500, 10, 10));

      expect(scrollTo).toHaveBeenCalledWith({ behavior: 'smooth', top: 580 });
      scroller.dispatchEvent(new Event('scrollend'));

      await expect(promise).resolves.toBeUndefined();
    });

    it('should resolve when the element cannot be found', async () => {
      const { scrollToElement } = setup(scrollerRef(makeScroller()));
      await expect(scrollToElement('missing-id')).resolves.toBeUndefined();
    });
  });
});
