/**
 * How a field says it is invalid, which is not one thing.
 *
 * @remarks
 * The text-like controls (text field, text area, autocomplete, select, category picker, date-time
 * picker) put `aria-invalid` on the control itself; the check controls (checkbox, radio, switch,
 * slider, file upload) put `data-error` on their wrapper. Both are matched in one query so the
 * result is the first invalid field in document order rather than the first of one family. The
 * value is part of the selector because a valid control renders `aria-invalid="false"` rather than
 * dropping the attribute.
 */
const INVALID_FIELD = '[aria-invalid="true"], [data-error]';

const CONTROL = 'input:not([type="hidden"]), textarea, select';

const FOCUSABLE = 'button, [tabindex]';

/**
 * Composable for revealing the first form field that failed validation.
 */
export function useFormErrorFocus(): {
  focusFirstError: (container?: HTMLElement | undefined) => Promise<void>;
} {
  function isAccordionOpen(accordion: HTMLElement): boolean {
    return accordion.dataset.state === 'open';
  }

  /**
   * Opens the accordion holding the field, if it is collapsed.
   *
   * @remarks
   * A collapsed element has no position to scroll to and cannot take focus, so the caller has to
   * wait for the expansion: doing both in the tick the trigger is clicked lands somewhere else on
   * the page.
   *
   * @param field - the invalid field, which may sit anywhere inside the accordion
   */
  async function expandAccordionAround(field: HTMLElement): Promise<void> {
    const accordion = field.closest<HTMLElement>('[data-accordion]');

    if (!accordion || isAccordionOpen(accordion))
      return;

    const accordionTrigger = accordion.querySelector<HTMLElement>('[data-accordion-trigger]');
    if (!accordionTrigger)
      return;

    accordionTrigger.click();
    await nextTick();
  }

  /**
   * The innermost control of the field, which is not always the element carrying the marker.
   *
   * @remarks
   * A check control marks its wrapper, and an autocomplete marks the activator that wraps its search
   * input. Landing on the wrapper looks focused and swallows typing until the control is opened with
   * a key, which is not where tabbing into the same field puts you. Inputs are preferred over other
   * focusable descendants so a decorative button beside the control cannot win.
   */
  function focusTargetOf(field: HTMLElement): HTMLElement {
    const control = field.querySelector<HTMLElement>(CONTROL);
    if (control)
      return control;

    if (field.matches(CONTROL))
      return field;

    return field.querySelector<HTMLElement>(FOCUSABLE) ?? field;
  }

  /**
   * Focuses the first form field that failed validation and scrolls it into view.
   *
   * @remarks
   * Doing nothing when the field already holds focus keeps the two callers from fighting: the save
   * button reveals the errors validation produced, and the error-count watcher reveals the ones the
   * backend reported, and either may arrive first. It also means a user who has started typing in
   * the field is not scrolled back to it.
   *
   * @param container - where to search; the whole document when omitted
   */
  async function focusFirstError(container?: HTMLElement | undefined): Promise<void> {
    const searchContainer = container ?? document;
    const errorElement = searchContainer.querySelector<HTMLElement>(INVALID_FIELD);

    if (!errorElement)
      return;

    await expandAccordionAround(errorElement);

    const target = focusTargetOf(errorElement);
    if (target === errorElement.ownerDocument.activeElement)
      return;

    target.focus({ preventScroll: true });
    errorElement.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    });
  }

  return {
    focusFirstError,
  };
}
