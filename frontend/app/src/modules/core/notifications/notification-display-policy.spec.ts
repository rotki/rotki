import { NotificationKind } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { displaysFor } from '@/modules/core/notifications/notification-display-policy';

describe('displaysFor', () => {
  it.each([
    [NotificationKind.ANNOUNCEMENT, true],
    [NotificationKind.REMINDER, true],
    [NotificationKind.RESULT, true],
    [NotificationKind.FAILURE, false],
  ])('should pop a %s notification: %s', (kind, expected) => {
    expect(displaysFor(kind)).toBe(expected);
  });
});
