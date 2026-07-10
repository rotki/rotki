import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useFormErrorScroll } from '@/modules/core/common/use-form-error-scroll';

describe('useFormErrorScroll', () => {
  let scrollIntoView: ReturnType<typeof vi.fn<(arg?: boolean | ScrollIntoViewOptions) => void>>;

  beforeEach(() => {
    scrollIntoView = vi.fn<(arg?: boolean | ScrollIntoViewOptions) => void>();
    Element.prototype.scrollIntoView = scrollIntoView;
    document.body.innerHTML = '';
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('should do nothing when there is no error element', async () => {
    document.body.innerHTML = '<div><input /></div>';
    const { scrollToFirstError } = useFormErrorScroll();
    await scrollToFirstError();
    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it('should scroll the first error element into view', async () => {
    document.body.innerHTML = '<div data-error>bad</div>';
    const { scrollToFirstError } = useFormErrorScroll();
    await scrollToFirstError();
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
  });

  it('should expand a collapsed accordion before scrolling', async () => {
    document.body.innerHTML = `
      <div data-accordion data-state="closed">
        <button data-accordion-trigger></button>
        <div data-error>bad</div>
      </div>
    `;
    const trigger = document.querySelector<HTMLElement>('[data-accordion-trigger]');
    const click = vi.fn();
    trigger?.addEventListener('click', click);

    const { scrollToFirstError } = useFormErrorScroll();
    await scrollToFirstError();

    expect(click).toHaveBeenCalledOnce();
    expect(scrollIntoView).toHaveBeenCalled();
  });

  it('should not click the trigger when the accordion is already open', async () => {
    document.body.innerHTML = `
      <div data-accordion data-state="open">
        <button data-accordion-trigger></button>
        <div data-error>bad</div>
      </div>
    `;
    const trigger = document.querySelector<HTMLElement>('[data-accordion-trigger]');
    const click = vi.fn();
    trigger?.addEventListener('click', click);

    const { scrollToFirstError } = useFormErrorScroll();
    await scrollToFirstError();

    expect(click).not.toHaveBeenCalled();
    expect(scrollIntoView).toHaveBeenCalled();
  });

  it('should only search within the provided container', async () => {
    document.body.innerHTML = `
      <div id="outside" data-error>outside</div>
      <div id="scope"><input /></div>
    `;
    const scope = document.querySelector<HTMLElement>('#scope');
    const { scrollToFirstError } = useFormErrorScroll();
    await scrollToFirstError(scope ?? undefined);
    expect(scrollIntoView).not.toHaveBeenCalled();
  });
});
