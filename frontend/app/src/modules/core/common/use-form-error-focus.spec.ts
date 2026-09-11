import type { Component } from 'vue';
import { RuiAutoComplete, RuiCheckbox, RuiTextField } from '@rotki/ui-library';
import { mount } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useFormErrorFocus } from '@/modules/core/common/use-form-error-focus';

describe('useFormErrorFocus', () => {
  let scrollIntoView: ReturnType<typeof vi.fn<(arg?: boolean | ScrollIntoViewOptions) => void>>;
  let container: HTMLElement;

  /**
   * Mounts the real library components, because the attributes they mark an invalid field with are
   * the whole contract here: a spec that builds its own `data-error` fixtures keeps passing when a
   * library release moves the marker, which is how the previous version of this went unnoticed.
   */
  function attach(component: Component, props: Record<string, unknown>): HTMLElement {
    return mount(component, { attachTo: container, props }).element;
  }

  beforeEach(() => {
    scrollIntoView = vi.fn<(arg?: boolean | ScrollIntoViewOptions) => void>();
    Element.prototype.scrollIntoView = scrollIntoView;
    document.body.innerHTML = '<div id="container"></div>';
    const element = document.querySelector<HTMLElement>('#container');
    assert(element);
    container = element;
  });

  it('should focus the input of an invalid text field', async () => {
    attach(RuiTextField, { errorMessages: ['boom'], label: 'name', modelValue: '' });

    const { focusFirstError } = useFormErrorFocus();
    await focusFirstError(container);

    expect(document.activeElement).toBe(container.querySelector('input'));
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
  });

  it('should skip a valid field, which renders aria-invalid="false"', async () => {
    attach(RuiTextField, { label: 'valid', modelValue: '' });
    const invalid = attach(RuiTextField, { errorMessages: ['boom'], label: 'invalid', modelValue: '' });

    const { focusFirstError } = useFormErrorFocus();
    await focusFirstError(container);

    expect(document.activeElement).toBe(invalid.querySelector('input'));
  });

  it('should focus the control inside a wrapper marked with data-error', async () => {
    const checkbox = attach(RuiCheckbox, { errorMessages: ['boom'], modelValue: false });

    const { focusFirstError } = useFormErrorFocus();
    await focusFirstError(container);

    expect(checkbox.querySelector('[data-error]')).not.toBeNull();
    expect(document.activeElement).toBe(checkbox.querySelector('input'));
  });

  it('should focus the search input of an autocomplete, not its activator', async () => {
    const auto = attach(RuiAutoComplete, { errorMessages: ['boom'], modelValue: undefined, options: ['a', 'b'] });

    const { focusFirstError } = useFormErrorFocus();
    await focusFirstError(container);

    // The activator is focusable and comes first, but it swallows typing until a key opens it.
    expect(auto.querySelector('[data-id="activator"]')).not.toBeNull();
    expect(document.activeElement).toBe(auto.querySelector('input'));
  });

  it('should do nothing when no field is invalid', async () => {
    attach(RuiTextField, { label: 'valid', modelValue: '' });

    const { focusFirstError } = useFormErrorFocus();
    await focusFirstError(container);

    expect(document.activeElement).toBe(document.body);
    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it('should expand a collapsed accordion before focusing what is inside it', async () => {
    container.innerHTML = `
      <div data-accordion data-state="closed">
        <button data-accordion-trigger></button>
        <input aria-invalid="true" />
      </div>
    `;
    const trigger = container.querySelector<HTMLElement>('[data-accordion-trigger]');
    const click = vi.fn();
    trigger?.addEventListener('click', click);

    const { focusFirstError } = useFormErrorFocus();
    await focusFirstError(container);

    expect(click).toHaveBeenCalledOnce();
    expect(document.activeElement).toBe(container.querySelector('input'));
  });

  it('should not click the trigger of an accordion that is already open', async () => {
    container.innerHTML = `
      <div data-accordion data-state="open">
        <button data-accordion-trigger></button>
        <input aria-invalid="true" />
      </div>
    `;
    const trigger = container.querySelector<HTMLElement>('[data-accordion-trigger]');
    const click = vi.fn();
    trigger?.addEventListener('click', click);

    const { focusFirstError } = useFormErrorFocus();
    await focusFirstError(container);

    expect(click).not.toHaveBeenCalled();
    expect(scrollIntoView).toHaveBeenCalled();
  });

  it('should leave the field alone when it already holds focus', async () => {
    const field = attach(RuiTextField, { errorMessages: ['boom'], label: 'name', modelValue: '' });
    const input = field.querySelector('input');
    assert(input);
    input.focus();

    const { focusFirstError } = useFormErrorFocus();
    await focusFirstError(container);

    expect(document.activeElement).toBe(input);
    expect(scrollIntoView).not.toHaveBeenCalled();

    // Revealed again once focus moves off it, so the silence above is the guard and not a miss.
    input.blur();
    await focusFirstError(container);

    expect(document.activeElement).toBe(input);
    expect(scrollIntoView).toHaveBeenCalledOnce();
  });

  it('should only search within the provided container', async () => {
    document.body.insertAdjacentHTML('beforeend', '<input id="outside" aria-invalid="true" />');
    attach(RuiTextField, { label: 'valid', modelValue: '' });

    const { focusFirstError } = useFormErrorFocus();
    await focusFirstError(container);

    expect(document.activeElement).not.toBe(document.querySelector('#outside'));
    expect(scrollIntoView).not.toHaveBeenCalled();
  });
});
