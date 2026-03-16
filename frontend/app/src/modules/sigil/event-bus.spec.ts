import { afterEach, describe, expect, it, vi } from 'vitest';
import { sigilBus } from '@/modules/sigil/event-bus';

describe('sigilBus', () => {
  afterEach(() => {
    sigilBus.all.clear();
  });

  it('should emit and receive session:ready', () => {
    const handler = vi.fn();
    sigilBus.on('session:ready', handler);

    sigilBus.emit('session:ready');

    expect(handler).toHaveBeenCalledOnce();
  });

  it('should emit and receive balances:loaded', () => {
    const handler = vi.fn();
    sigilBus.on('balances:loaded', handler);

    sigilBus.emit('balances:loaded');

    expect(handler).toHaveBeenCalledOnce();
  });

  it('should emit and receive history:ready', () => {
    const handler = vi.fn();
    sigilBus.on('history:ready', handler);

    sigilBus.emit('history:ready');

    expect(handler).toHaveBeenCalledOnce();
  });

  it('should not call handler after off', () => {
    const handler = vi.fn();
    sigilBus.on('session:ready', handler);
    sigilBus.off('session:ready', handler);

    sigilBus.emit('session:ready');

    expect(handler).not.toHaveBeenCalled();
  });
});
