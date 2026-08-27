import type { MaybeRef, Ref, ShallowRef } from 'vue';
import { startPromise } from '@shared/utils';
import { defaultDocument } from '@vueuse/core';

const SCROLL_SETTLE_TIMEOUT = 1500;
const SCROLL_TOP_MARGIN = 20;

/**
 * Smooth-scrolls `parent` so `element` sits just below its top edge, resolving once the scroll settles
 * or the safety timeout fires, whichever comes first.
 *
 * Deliberately outside the composable: it owns its own teardown. Both the safety timer and the one-shot
 * `scrollend` listener are released by whichever path finishes first, so there is nothing for a scope
 * hook to clean up, and the DOM maths is testable on its own.
 */
async function scrollIntoContainer(parent: HTMLElement, element: Element): Promise<void> {
  const parentRect = parent.getBoundingClientRect();
  const elementRect = element.getBoundingClientRect();
  const targetTop = parent.scrollTop + elementRect.top - parentRect.top - SCROLL_TOP_MARGIN;

  if (Math.abs(parent.scrollTop - targetTop) < 1)
    return;

  return new Promise<void>((resolve) => {
    let safetyTimeout: ReturnType<typeof setTimeout> | undefined;

    function finish(): void {
      clearTimeout(safetyTimeout);
      parent.removeEventListener('scrollend', finish);
      resolve();
    }

    safetyTimeout = setTimeout(finish, SCROLL_SETTLE_TIMEOUT);
    parent.addEventListener('scrollend', finish, { once: true });
    parent.scrollTo({ behavior: 'smooth', top: targetTop });
  });
}

interface Nav {
  id: string;
  label: string;
}

interface UseSettingsScrollSpyOptions {
  /**
   * Section entries in document order, whose `id` must match the element ids on the page. Read once at
   * setup, so later changes to the list are not picked up.
   */
  navigation: MaybeRef<Nav[]>;
  /**
   * Template ref of the scrolling container the sections live in. It is `null` until mount, and while
   * null viewport checks report false and scrolling is a no-op.
   */
  scroller: Readonly<ShallowRef<HTMLDivElement | null>>;
}

interface UseSettingsScrollSpyReturn {
  currentId: Readonly<Ref<string>>;
  isElementInViewport: (el: Element) => boolean;
  scrollToElement: (el?: string | Element) => Promise<void>;
}

export function useSettingsScrollSpy({ navigation, scroller }: UseSettingsScrollSpyOptions): UseSettingsScrollSpyReturn {
  const navItems = toValue(navigation);
  const currentId = ref<string>(navItems[0]?.id ?? '');

  function isElementInViewport(el: Element): boolean {
    const parent = get(scroller);
    if (!parent)
      return false;

    const parentRect = parent.getBoundingClientRect();
    const elementRect = el.getBoundingClientRect();

    return (
      elementRect.top < parentRect.bottom
      && elementRect.bottom > parentRect.top
      && elementRect.left < parentRect.right
      && elementRect.right > parentRect.left
    );
  }

  function resolveEdgeId(parent: HTMLDivElement): string | undefined {
    if (parent.scrollTop === 0)
      return navItems.at(0)?.id ?? '';
    if (parent.scrollTop + parent.clientHeight >= parent.scrollHeight - 10)
      return navItems.at(-1)?.id ?? '';
    return undefined;
  }

  function checkVisibility(): void {
    const parent = get(scroller);
    if (parent) {
      const edgeId = resolveEdgeId(parent);
      if (edgeId !== undefined) {
        set(currentId, edgeId);
        return;
      }
    }

    for (const nav of navItems) {
      const element = defaultDocument?.getElementById(nav.id);
      if (element && isElementInViewport(element)) {
        set(currentId, nav.id);
        return;
      }
    }
    set(currentId, navItems[0]?.id ?? '');
  }

  async function scrollToElement(el?: string | Element): Promise<void> {
    if (!el)
      return;

    const element = typeof el === 'string' ? defaultDocument?.getElementById(el) : el;
    const parent = get(scroller);
    if (element && parent)
      await scrollIntoContainer(parent, element);
  }

  const throttledCheckVisibility = useThrottleFn(checkVisibility, 100);

  function onViewportChange(): void {
    startPromise(throttledCheckVisibility());
  }

  useEventListener(scroller, 'scroll', onViewportChange);
  useEventListener(window, 'resize', onViewportChange);

  onMounted(() => {
    checkVisibility();
  });

  return {
    currentId: readonly(currentId),
    isElementInViewport,
    scrollToElement,
  };
}
