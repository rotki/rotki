import { type HighlightRequest, useSettingsHighlight } from '@/modules/settings/use-settings-highlight';

const HIGHLIGHT_CLASSES = ['outline', 'outline-2', 'outline-offset-[12px]', 'rounded-sm'] as const;

interface UseSettingsPageHighlightOptions {
  scrollToElement: (el?: string | Element) => Promise<void>;
  isElementInViewport: (el: Element) => boolean;
}

export function useSettingsPageHighlight({ scrollToElement, isElementInViewport }: UseSettingsPageHighlightOptions): void {
  const { clearHighlight, highlightTarget } = useSettingsHighlight();

  let activeHighlight: { element: HTMLElement; animation: Animation } | undefined;

  function applyHighlight(element: HTMLElement): void {
    if (activeHighlight) {
      activeHighlight.animation.cancel();
      activeHighlight.element.classList.remove(...HIGHLIGHT_CLASSES);
    }

    element.classList.add(...HIGHLIGHT_CLASSES);

    const animation: Animation = element.animate([
      { outlineColor: '#eab308', offset: 0 },
      { outlineColor: '#eab308', offset: 0.33 },
      { outlineColor: 'transparent', offset: 1 },
    ], { duration: 700, fill: 'forwards' });

    activeHighlight = { animation, element };

    animation.onfinish = (): void => {
      element.classList.remove(...HIGHLIGHT_CLASSES);
      activeHighlight = undefined;
      clearHighlight();
    };
  }

  async function scrollAndHighlight(targetId: string): Promise<void> {
    const element = document.getElementById(targetId);
    if (!element)
      return;

    clearHighlight();

    if (!isElementInViewport(element))
      await scrollToElement(element);

    applyHighlight(element);
  }

  function getHighlightTargetId(request: HighlightRequest): string {
    return request.highlightId ?? request.categoryId;
  }

  // Same-page: element already exists in DOM
  watch(highlightTarget, async (request: HighlightRequest | undefined) => {
    if (!request)
      return;

    let cancelled: boolean = false;
    onWatcherCleanup(() => {
      cancelled = true;
    });

    await nextTick();
    if (cancelled)
      return;
    await scrollAndHighlight(getHighlightTargetId(request));
  });

  // Cross-page: handle pending highlight request after mount
  onMounted(async () => {
    const request: HighlightRequest | undefined = get(highlightTarget);
    if (request) {
      await nextTick();
      await scrollAndHighlight(getHighlightTargetId(request));
    }
  });
}
