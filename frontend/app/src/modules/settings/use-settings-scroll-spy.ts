import type { MaybeRef, Ref, ShallowRef } from 'vue';

interface Nav {
  id: string;
  label: string;
}

interface UseSettingsScrollSpyOptions {
  navigation: MaybeRef<Nav[]>;
  scroller: Readonly<ShallowRef<HTMLDivElement | null>>;
}

interface UseSettingsScrollSpyReturn {
  currentId: Ref<string>;
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

  function checkVisibility(): void {
    const parent = get(scroller);
    if (parent) {
      if (parent.scrollTop === 0) {
        set(currentId, navItems.at(0)?.id ?? '');
        return;
      }
      if (parent.scrollTop + parent.clientHeight >= parent.scrollHeight - 10) {
        set(currentId, navItems.at(-1)?.id ?? '');
        return;
      }
    }

    for (const nav of navItems) {
      const element = document.getElementById(nav.id);
      if (element && isElementInViewport(element)) {
        set(currentId, nav.id);
        return;
      }
    }
    set(currentId, navItems[0]?.id ?? '');
  }

  async function scrollToElement(el?: string | Element): Promise<void> {
    return new Promise((resolve) => {
      if (!el) {
        resolve();
        return;
      }
      const element = typeof el === 'string' ? document.getElementById(el) : el;
      const parent = get(scroller);
      if (element && parent) {
        const parentRect = parent.getBoundingClientRect();
        const elementRect = element.getBoundingClientRect();
        const targetTop = parent.scrollTop + elementRect.top - parentRect.top - 20;

        if (Math.abs(parent.scrollTop - targetTop) < 1) {
          resolve();
          return;
        }

        const safetyTimeout: ReturnType<typeof setTimeout> = setTimeout(resolve, 1500);
        parent.addEventListener('scrollend', () => {
          clearTimeout(safetyTimeout);
          resolve();
        }, { once: true });
        parent.scrollTo({ behavior: 'smooth', top: targetTop });
      }
      else {
        resolve();
      }
    });
  }

  const throttledCheckVisibility = useThrottleFn(checkVisibility, 100);

  useEventListener(scroller, 'scroll', throttledCheckVisibility);
  useEventListener(window, 'resize', throttledCheckVisibility);

  onMounted(() => {
    checkVisibility();
  });

  return {
    currentId,
    isElementInViewport,
    scrollToElement,
  };
}
