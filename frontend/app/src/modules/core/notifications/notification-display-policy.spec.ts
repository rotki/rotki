import { Priority } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { DEFAULT_PRIORITY, displaysFor } from '@/modules/core/notifications/notification-display-policy';

describe('displaysFor', () => {
  it.each([
    [Priority.ACTION, true],
    [Priority.HIGH, true],
    [Priority.NORMAL, false],
    [Priority.BULK, false],
  ])('should pop a %s notification: %s', (priority, expected) => {
    expect(displaysFor(priority)).toBe(expected);
  });

  it('should classify an unclassified notification as the default priority', () => {
    expect(displaysFor()).toBe(displaysFor(DEFAULT_PRIORITY));
  });

  it('should record the unclassified without popping it, so forgetting to classify cannot interrupt', () => {
    expect(displaysFor(undefined)).toBe(false);
  });
});
