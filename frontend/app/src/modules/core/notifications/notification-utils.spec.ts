import { NotificationKind, Severity } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { createNotification } from '@/modules/core/notifications/notification-utils';

describe('createNotification', () => {
  it('should build a silent placeholder when given no payload', () => {
    expect(createNotification()).toMatchObject({ display: false, message: '', title: '' });
  });

  it('should derive display from the kind of a payload that does not ask', () => {
    const popped = createNotification(1, { kind: NotificationKind.RESULT, message: 'm', severity: Severity.INFO, title: 't' });
    const stored = createNotification(2, { kind: NotificationKind.FAILURE, message: 'm', severity: Severity.INFO, title: 't' });

    expect(popped.display).toBe(true);
    expect(stored.display).toBe(false);
  });

  it('should let a payload silence itself against its kind', () => {
    const silenced = createNotification(1, {
      display: false,
      kind: NotificationKind.RESULT,
      message: 'm',
      severity: Severity.INFO,
      title: 't',
    });

    expect(silenced.display).toBe(false);
  });

  it('should keep the kind the caller gave, so the drawer files it there', () => {
    expect(createNotification(1, { kind: NotificationKind.FAILURE, message: 'm', severity: Severity.ERROR, title: 't' }).kind)
      .toBe(NotificationKind.FAILURE);
  });

  it('should keep the severity the caller gave instead of filing it as news', () => {
    expect(createNotification(1, { kind: NotificationKind.RESULT, message: 'm', severity: Severity.ERROR, title: 't' }).severity)
      .toBe(Severity.ERROR);
  });
});
