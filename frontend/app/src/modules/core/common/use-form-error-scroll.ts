/**
 * Composable for scrolling to the first form field with validation error
 */
export function useFormErrorScroll(): {
  scrollToFirstError: (container?: HTMLElement | undefined) => Promise<void>;
} {
  /**
   * Check if the accordion is currently open using data-state attribute
   */
  function isAccordionOpen(accordion: HTMLElement): boolean {
    return accordion.dataset.state === 'open';
  }

  /**
   * Scrolls to the first form field that has a validation error.
   *
   * @remarks
   * An error inside a collapsed accordion is opened first, and the scroll waits a tick for that:
   * a collapsed element has no position to scroll to, so scrolling in the same tick as the click
   * lands somewhere else on the page.
   *
   * @param container - where to search; the whole document when omitted
   */
  async function scrollToFirstError(container?: HTMLElement | undefined): Promise<void> {
    const searchContainer = container ?? document;
    const errorElement = searchContainer.querySelector<HTMLElement>('[data-error]');

    if (!errorElement)
      return;

    const accordion = errorElement.closest<HTMLElement>('[data-accordion]');

    if (accordion && !isAccordionOpen(accordion)) {
      const accordionTrigger = accordion.querySelector<HTMLElement>('[data-accordion-trigger]');
      if (accordionTrigger) {
        accordionTrigger.click();
        await nextTick();
      }
    }

    errorElement.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    });
  }

  return {
    scrollToFirstError,
  };
}
