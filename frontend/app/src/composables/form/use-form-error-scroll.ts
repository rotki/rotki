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
   * If the error field is inside a collapsed accordion, it will expand the accordion first.
   *
   * @param container - Optional container element to search within
   */
  async function scrollToFirstError(container?: HTMLElement | undefined): Promise<void> {
    const searchContainer = container ?? document;
    const errorElement = searchContainer.querySelector<HTMLElement>('[data-error]');

    if (!errorElement)
      return;

    // Check if the error element is inside an accordion that needs to be expanded
    const accordion = errorElement.closest<HTMLElement>('[data-accordion]');

    if (accordion && !isAccordionOpen(accordion)) {
      // Find the accordion trigger and click it to expand
      const accordionTrigger = accordion.querySelector<HTMLElement>('[data-accordion-trigger]');
      if (accordionTrigger) {
        accordionTrigger.click();
        // Wait for the accordion to expand
        await nextTick();
      }
    }

    // Scroll the error element into view
    errorElement.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    });
  }

  return {
    scrollToFirstError,
  };
}
