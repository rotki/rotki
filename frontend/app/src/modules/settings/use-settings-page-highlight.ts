import { type HighlightRequest, useSettingsHighlight } from '@/modules/settings/use-settings-highlight';

// A brief background flash, rounded and with horizontal padding, so the highlighted row reads as a
// contained highlight instead of a bare outline hugging the text. `-mx-4` cancels the `px-4` for layout
// (the surrounding content column already pads by the same amount), so nothing shifts while it is applied.
const HIGHLIGHT_CLASSES = ['rounded-lg', 'px-4', '-mx-4'] as const;

/** The rui primary, exposed as a theme-aware `r, g, b` triplet; falls back to the light-theme value. */
const FALLBACK_PRIMARY = '78, 91, 166';

interface UseSettingsPageHighlightOptions {
  /**
   * Scrolls the settings page container to the target. Awaited before the highlight animation starts, so
   * it must resolve once the smooth scroll has settled (or timed out).
   */
  scrollToElement: (el?: string | Element) => Promise<void>;
  /**
   * Decides whether scrolling can be skipped: a target already visible is highlighted in place, avoiding
   * a jump when the user is looking at it.
   */
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

    const primary = getComputedStyle(element).getPropertyValue('--rui-primary-main').trim() || FALLBACK_PRIMARY;
    const tint = `rgba(${primary}, 0.2)`;

    const animation: Animation = element.animate([
      { backgroundColor: tint, offset: 0 },
      { backgroundColor: tint, offset: 0.6 },
      { backgroundColor: 'transparent', offset: 1 },
    ], { duration: 1500, easing: 'ease-out', fill: 'forwards' });

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
