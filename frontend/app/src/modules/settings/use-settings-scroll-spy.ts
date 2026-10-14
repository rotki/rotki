import type { MaybeRef, Ref, ShallowRef } from 'vue';
import { startPromise } from '@shared/utils';
import { defaultDocument, promiseTimeout } from '@vueuse/core';

const SCROLL_SETTLE_TIMEOUT = 1500;
const SCROLL_TOP_MARGIN = 20;
const CHECK_THROTTLE = 100;
/** How far down the scroller, as a share of its height, a section's top must pass to count as read. */
const READING_LINE = 0.3;

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

  /**
   * The section being read: the last one whose top has passed a line a third of the way down the
   * scroller, so a section only counts once it fills the view rather than when its first pixel shows.
   * Falls back to the first section, which also covers sections not rendered yet.
   */
  function resolveReadingId(parent: HTMLDivElement): string {
    const line = parent.getBoundingClientRect().top + parent.clientHeight * READING_LINE;
    let reading = navItems[0]?.id ?? '';
    for (const nav of navItems) {
      const element = defaultDocument?.getElementById(nav.id);
      if (element && element.getBoundingClientRect().top <= line)
        reading = nav.id;
    }
    return reading;
  }

  /** Set while a click scrolls to its section, which stays selected even where it cannot reach the top. */
  let pinned = false;

  function checkVisibility(): void {
    if (pinned)
      return;

    const parent = get(scroller);
    if (!parent) {
      set(currentId, navItems[0]?.id ?? '');
      return;
    }

    set(currentId, resolveEdgeId(parent) ?? resolveReadingId(parent));
  }

  async function scrollToElement(el?: string | Element): Promise<void> {
    if (!el)
      return;

    const element = typeof el === 'string' ? defaultDocument?.getElementById(el) : el;
    const parent = get(scroller);
    if (!element || !parent)
      return;

    const navId = navItems.find(nav => nav.id === element.id)?.id;
    if (navId === undefined) {
      await scrollIntoContainer(parent, element);
      return;
    }

    set(currentId, navId);
    pinned = true;
    try {
      await scrollIntoContainer(parent, element);
      // the throttled check still due from the scroll would undo the choice
      await promiseTimeout(CHECK_THROTTLE);
    }
    finally {
      pinned = false;
    }
  }

  const throttledCheckVisibility = useThrottleFn(checkVisibility, CHECK_THROTTLE, true);

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
