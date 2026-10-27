import { describe, expect, it, vi } from 'vitest';
import { useDrawerDismiss } from '@/modules/accounts/details/use-drawer-dismiss';

function keydown(key: string, init: KeyboardEventInit = {}): KeyboardEvent {
  return new KeyboardEvent('keydown', { cancelable: true, key, ...init });
}

describe('modules/accounts/details/use-drawer-dismiss', () => {
  it('should close the drawer on Escape and keep the key from going further', () => {
    const close = vi.fn<() => void>();
    const { onKeydown } = useDrawerDismiss({ close, open: true });
    const event = keydown('Escape');

    onKeydown(event);

    expect(close).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
  });

  it('should leave other keys alone', () => {
    const close = vi.fn<() => void>();
    const { onKeydown } = useDrawerDismiss({ close, open: true });

    onKeydown(keydown('Enter'));

    expect(close).not.toHaveBeenCalled();
  });

  it('should let something inside the drawer that took the Escape keep it', () => {
    const close = vi.fn<() => void>();
    const { onKeydown } = useDrawerDismiss({ close, open: true });
    const event = keydown('Escape');
    event.preventDefault();

    onKeydown(event);

    expect(close).not.toHaveBeenCalled();
  });

  it('should leave an Escape that only cancels an IME composition', () => {
    const close = vi.fn<() => void>();
    const { onKeydown } = useDrawerDismiss({ close, open: true });

    onKeydown(keydown('Escape', { isComposing: true }));

    expect(close).not.toHaveBeenCalled();
  });

  it('should do nothing while the drawer is closed', () => {
    const close = vi.fn<() => void>();
    const { onKeydown } = useDrawerDismiss({ close, open: false });

    onKeydown(keydown('Escape'));

    expect(close).not.toHaveBeenCalled();
  });
});
