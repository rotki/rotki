import type { HighlightRequest } from '@/modules/settings/use-settings-highlight';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import { SettingsCategoryIds, SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { useSettingsPageHighlight } from '@/modules/settings/use-settings-page-highlight';

const mockClearHighlight = vi.fn();
const mockHighlightTarget = ref<HighlightRequest>();

vi.mock('@/modules/settings/use-settings-highlight', () => ({
  useSettingsHighlight: vi.fn(() => ({
    clearHighlight: mockClearHighlight,
    highlightTarget: mockHighlightTarget,
  })),
}));

const FOO = SettingsHighlightIds.ABBREVIATION;
const BAR = SettingsHighlightIds.AMOUNT_FORMAT;
const CATEGORY = SettingsCategoryIds.AMOUNT;
const MISSING = SettingsHighlightIds.CSV_EXPORT;

function addTarget(id: string): { element: HTMLElement; animation: Animation; animateSpy: Mock; cancelSpy: Mock } {
  const element = document.createElement('div');
  element.id = id;
  document.body.appendChild(element);
  // createMock supplies an `Animation`-typed stub; the SUT only reads `cancel`
  // and assigns `onfinish`, which lands on the underlying mock and reads back.
  const cancelSpy = vi.fn();
  const animation = createMock<Animation>({ cancel: cancelSpy });
  const animateSpy = vi.fn(() => animation);
  element.animate = animateSpy;
  return { animateSpy, animation, cancelSpy, element };
}

interface HarnessOptions {
  isElementInViewport?: (el: Element) => boolean;
}

const wrappers: VueWrapper[] = [];

function mountHighlight(options: HarnessOptions = {}): {
  scrollToElement: ReturnType<typeof vi.fn>;
  isElementInViewport: ReturnType<typeof vi.fn>;
} {
  const scrollToElement = vi.fn(async (): Promise<void> => {});
  const isElementInViewport = vi.fn(options.isElementInViewport ?? ((): boolean => true));
  wrappers.push(mount(defineComponent({
    setup(): () => VNode {
      useSettingsPageHighlight({ isElementInViewport, scrollToElement });
      return () => h('div');
    },
  })));
  return { isElementInViewport, scrollToElement };
}

describe('useSettingsPageHighlight', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockHighlightTarget, undefined);
    document.body.innerHTML = '';
  });

  afterEach(() => {
    wrappers.splice(0).forEach(wrapper => wrapper.unmount());
    document.body.innerHTML = '';
  });

  describe('same-page highlighting', () => {
    it('should scroll and highlight when the target enters the DOM', async () => {
      const { animation, animateSpy, element } = addTarget(FOO);
      const { scrollToElement } = mountHighlight({ isElementInViewport: () => false });

      set(mockHighlightTarget, { categoryId: CATEGORY, highlightId: FOO });
      await flushPromises();

      expect(scrollToElement).toHaveBeenCalledWith(element);
      expect(element.classList.contains('rounded-lg')).toBe(true);
      expect(animateSpy).toHaveBeenCalledOnce();
      expect(animation.onfinish).toBeTypeOf('function');
    });

    it('should not scroll when the element is already in viewport', async () => {
      addTarget(FOO);
      const { scrollToElement } = mountHighlight({ isElementInViewport: () => true });

      set(mockHighlightTarget, { categoryId: CATEGORY, highlightId: FOO });
      await flushPromises();

      expect(scrollToElement).not.toHaveBeenCalled();
    });

    it('should do nothing when no element matches the target id', async () => {
      const { scrollToElement } = mountHighlight();

      set(mockHighlightTarget, { categoryId: CATEGORY, highlightId: MISSING });
      await flushPromises();

      expect(scrollToElement).not.toHaveBeenCalled();
      expect(mockClearHighlight).not.toHaveBeenCalled();
    });

    it('should ignore a cleared target', async () => {
      addTarget(FOO);
      const { scrollToElement } = mountHighlight();

      set(mockHighlightTarget, undefined);
      await flushPromises();

      expect(scrollToElement).not.toHaveBeenCalled();
    });

    it('should fall back to the category id when no highlight id is given', async () => {
      const { element } = addTarget(CATEGORY);
      mountHighlight({ isElementInViewport: () => true });

      set(mockHighlightTarget, { categoryId: CATEGORY });
      await flushPromises();

      expect(element.classList.contains('rounded-lg')).toBe(true);
    });
  });

  describe('animation lifecycle', () => {
    it('should clean up classes and clear the highlight when the animation finishes', async () => {
      const { animation, element } = addTarget(FOO);
      mountHighlight({ isElementInViewport: () => true });

      set(mockHighlightTarget, { categoryId: CATEGORY, highlightId: FOO });
      await flushPromises();
      mockClearHighlight.mockClear();

      animation.onfinish?.(createMock<AnimationPlaybackEvent>());

      expect(element.classList.contains('rounded-lg')).toBe(false);
      expect(mockClearHighlight).toHaveBeenCalledOnce();
    });

    it('should cancel the previous animation before starting a new one', async () => {
      const first = addTarget(FOO);
      const second = addTarget(BAR);
      mountHighlight({ isElementInViewport: () => true });

      set(mockHighlightTarget, { categoryId: CATEGORY, highlightId: FOO });
      await flushPromises();

      set(mockHighlightTarget, { categoryId: CATEGORY, highlightId: BAR });
      await flushPromises();

      expect(first.cancelSpy).toHaveBeenCalledOnce();
      expect(first.element.classList.contains('rounded-lg')).toBe(false);
      expect(second.element.classList.contains('rounded-lg')).toBe(true);
    });
  });

  describe('cross-page highlighting', () => {
    it('should highlight a pending target present at mount time', async () => {
      const { element } = addTarget(FOO);
      set(mockHighlightTarget, { categoryId: CATEGORY, highlightId: FOO });

      const { scrollToElement } = mountHighlight({ isElementInViewport: () => false });
      await flushPromises();

      expect(scrollToElement).toHaveBeenCalledWith(element);
      expect(element.classList.contains('rounded-lg')).toBe(true);
    });

    it('should do nothing at mount when there is no pending target', async () => {
      addTarget(FOO);
      const { scrollToElement } = mountHighlight();
      await flushPromises();

      expect(scrollToElement).not.toHaveBeenCalled();
    });
  });
});
