import { describe, expect, it } from 'vitest';
import { focusInput } from './focus-input';

function componentWith(html: string): { $el: Element } {
  const root = document.createElement('div');
  root.innerHTML = html;
  document.body.append(root);
  return { $el: root };
}

describe('modules/auth/login/focusInput', () => {
  it('should focus the first visible input', () => {
    const component = componentWith('<input id="first"><input id="second">');

    focusInput(component);

    expect(document.activeElement?.id).toBe('first');
  });

  it('should skip hidden inputs', () => {
    const component = componentWith('<input type="hidden" id="hidden"><input id="visible">');

    focusInput(component);

    expect(document.activeElement?.id).toBe('visible');
  });

  it('should do nothing when the component renders no input', () => {
    const component = componentWith('<span>no input here</span>');

    expect(() => focusInput(component)).not.toThrow();
  });

  it('should tolerate null and undefined', () => {
    expect(() => focusInput(null)).not.toThrow();
    expect(() => focusInput(undefined)).not.toThrow();
  });

  it('should tolerate a component without a root element', () => {
    expect(() => focusInput({})).not.toThrow();
    expect(() => focusInput({ $el: undefined })).not.toThrow();
  });
});
