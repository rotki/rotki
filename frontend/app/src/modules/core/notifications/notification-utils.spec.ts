import { Priority, Severity } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { createNotification } from '@/modules/core/notifications/notification-utils';

describe('createNotification', () => {
  it('should build a silent placeholder when given no payload', () => {
    expect(createNotification()).toMatchObject({ display: false, message: '', title: '' });
  });

  it('should derive display from the priority of a payload that does not ask', () => {
    const popped = createNotification(1, { message: 'm', priority: Priority.ACTION, title: 't' });
    const stored = createNotification(2, { message: 'm', priority: Priority.BULK, title: 't' });

    expect(popped.display).toBe(true);
    expect(stored.display).toBe(false);
  });

  it('should let a payload silence itself against its priority', () => {
    const silenced = createNotification(1, {
      display: false,
      message: 'm',
      priority: Priority.ACTION,
      title: 't',
    });

    expect(silenced.display).toBe(false);
  });

  it('should record the priority it defaulted to, so the drawer sorts on the same value', () => {
    expect(createNotification(1, { message: 'm', severity: Severity.ERROR, title: 't' }).priority)
      .toBe(createNotification(2, { message: 'm', title: 't' }).priority);
  });
});
