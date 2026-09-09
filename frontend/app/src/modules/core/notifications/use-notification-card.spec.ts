import { type NotificationAction, NotificationCategory, type NotificationData, Priority, Severity } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { NOTIFICATION_MAX_HEIGHT, useNotificationCard } from './use-notification-card';

const { copyToClipboard } = vi.hoisted(() => ({
  copyToClipboard: vi.fn(),
}));

vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual<typeof import('@vueuse/core')>('@vueuse/core');
  return {
    ...actual,
    useClipboard: (): Record<string, unknown> => ({ copy: copyToClipboard }),
  };
});

function notification(overrides: Partial<NotificationData> = {}): NotificationData {
  return {
    category: NotificationCategory.DEFAULT,
    date: new Date('2026-03-04T05:06:07Z'),
    display: true,
    duration: 5000,
    id: 42,
    message: 'the message',
    read: false,
    severity: Severity.INFO,
    title: 'the title',
    ...overrides,
  };
}

const dismiss = vi.fn();
const height = ref<number>(0);
let scope: ReturnType<typeof effectScope>;

function card(data: NotificationData = notification()): ReturnType<typeof useNotificationCard> {
  scope = effectScope();
  return scope.run(() => useNotificationCard(() => data, { dismiss, height }))!;
}

describe('modules/core/notifications/useNotificationCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(height, 0);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('actions', () => {
    it('should be empty when the notification carries none', () => {
      const { actions } = card();

      expect(get(actions)).toEqual([]);
    });

    it('should wrap a single action in a list', () => {
      const action: NotificationAction = { action: vi.fn(), label: 'Retry' };

      const { actions } = card(notification({ action }));

      expect(get(actions)).toEqual([action]);
    });

    it('should pass a list of actions through unchanged', () => {
      const first: NotificationAction = { action: vi.fn(), label: 'Retry' };
      const second: NotificationAction = { action: vi.fn(), label: 'Ignore' };

      const { actions } = card(notification({ action: [first, second] }));

      expect(get(actions)).toEqual([first, second]);
    });
  });

  describe('severity styling', () => {
    it.each([
      [Severity.ERROR, 'lu-circle-alert', 'bg-rui-error'],
      [Severity.INFO, 'lu-circle-alert', 'bg-rui-info'],
      [Severity.WARNING, 'lu-siren', 'bg-rui-warning'],
      [Severity.REMINDER, 'lu-alarm-clock', 'bg-rui-secondary'],
    ])('should pick the icon and circle for %s', (severity, expectedIcon, expectedCircle) => {
      const { circleBgClass, icon } = card(notification({ severity }));

      expect(get(icon)).toBe(expectedIcon);
      expect(get(circleBgClass)).toBe(expectedCircle);
    });

    it.each([
      [Severity.ERROR, 'error', '!bg-rui-error/10', '!to-rui-error/10'],
      [Severity.INFO, 'info', '!bg-rui-info/10', '!to-rui-info/10'],
      [Severity.WARNING, 'warning', '!bg-rui-warning/10', '!to-rui-warning/10'],
      [Severity.REMINDER, 'reminder', '!bg-rui-secondary/10', '!to-rui-secondary/10'],
    ])('should derive the colour classes for %s', (severity, expectedColor, expectedBg, expectedButton) => {
      const { color, colorBgClass, expandButtonClass } = card(notification({ severity }));

      expect(get(color)).toBe(expectedColor);
      expect(get(colorBgClass)).toBe(expectedBg);
      expect(get(expandButtonClass)).toBe(expectedButton);
    });

    it('should fall back when the severity is not one it knows', () => {
      // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- exercising the defensive default arm
      const unknown = 'unknown' as Severity;

      const { circleBgClass, color, colorBgClass, expandButtonClass, icon } = card(notification({ severity: unknown }));

      expect(get(icon)).toBe('lu-circle-alert');
      expect(get(circleBgClass)).toBe('bg-rui-success');
      expect(get(color)).toBe('');
      expect(get(colorBgClass)).toBe('');
      expect(get(expandButtonClass)).toBe('');
    });

    it('should keep colour on severity when the notification carries an action', () => {
      const { circleBgClass, color, colorBgClass } = card(notification({
        action: { action: vi.fn(), label: 'Retry' },
        severity: Severity.ERROR,
      }));

      expect(get(color)).toBe('error');
      expect(get(colorBgClass)).toBe('!bg-rui-error/10');
      expect(get(circleBgClass)).toBe('bg-rui-error');
    });
  });

  describe('marking what needs the user', () => {
    it('should rail a notification that only the user can resolve', () => {
      const { actionRailClass } = card(notification({ priority: Priority.ACTION }));

      expect(get(actionRailClass)).toBe('border-l-4 !border-l-rui-primary');
    });

    it.each([Priority.HIGH, Priority.NORMAL, Priority.BULK])('should leave a %s notification unrailed', (priority) => {
      const { actionRailClass } = card(notification({ priority }));

      expect(get(actionRailClass)).toBe('');
    });

    it('should rail on priority rather than on carrying a button', () => {
      const withButton = card(notification({ action: { action: vi.fn(), label: 'Retry' }, priority: Priority.HIGH }));
      const withoutButton = card(notification({ priority: Priority.ACTION }));

      expect(get(withButton.actionRailClass)).toBe('');
      expect(get(withoutButton.actionRailClass)).not.toBe('');
    });
  });

  describe('when the notification arrived', () => {
    it('should report the date in milliseconds', () => {
      const date = new Date('2026-03-04T05:06:07Z');

      const { timestamp } = card(notification({ date }));

      expect(get(timestamp)).toBe(date.getTime());
    });

    it('should still report it when the date came back from serialization as a string', () => {
      const date = new Date('2026-03-04T05:06:07Z');
      // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- a persisted notification rehydrates with a string date
      const serialized = date.toISOString() as unknown as Date;

      const { timestamp } = card(notification({ date: serialized }));

      expect(get(timestamp)).toBe(date.getTime());
    });
  });

  describe('the action icon', () => {
    it('should use the action icon when the library has it', () => {
      const { getIcon } = card();

      expect(getIcon({ action: vi.fn(), icon: 'lu-trash-2', label: 'Delete' })).toBe('lu-trash-2');
    });

    it.each([
      ['a name the library does not have', 'not-an-icon'],
      ['no name at all', undefined],
    ])('should fall back to an arrow given %s', (_case, icon) => {
      const { getIcon } = card();

      expect(getIcon({ action: vi.fn(), icon, label: 'Go' })).toBe('lu-arrow-right');
    });
  });

  describe('running an action', () => {
    it('should run it and dismiss the notification it belongs to', () => {
      const action = vi.fn();

      const { doAction } = card(notification({ id: 7 }));
      doAction({ action, label: 'Retry' });

      expect(action).toHaveBeenCalledOnce();
      expect(dismiss).toHaveBeenCalledWith(7);
    });

    it('should leave a persisting action on screen', () => {
      const action = vi.fn();

      const { doAction } = card();
      doAction({ action, label: 'Retry', persist: true });

      expect(action).toHaveBeenCalledOnce();
      expect(dismiss).not.toHaveBeenCalled();
    });

    it('should still dismiss when the action has nothing to run', () => {
      const { doAction } = card(notification({ id: 9 }));
      // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- an action with no callback is what a link-only action looks like
      doAction({ label: 'Open' } as NotificationAction);

      expect(dismiss).toHaveBeenCalledWith(9);
    });
  });

  describe('copying the message', () => {
    it('should copy the message as written', async () => {
      const { copy } = card(notification({ message: 'boom' }));
      await copy();

      expect(copyToClipboard).toHaveBeenCalledWith('boom');
    });

    it('should resolve the translation parameters before copying', async () => {
      const { copy } = card(notification({
        i18nParam: {
          choice: 1,
          message: 'notification_messages.missing_api_key',
          props: { location: 'ethereum', service: 'etherscan', url: 'https://example.com' },
        },
        message: 'the untranslated message',
      }));
      await copy();

      expect(copyToClipboard).toHaveBeenCalledWith(
        'notification_messages.missing_api_key::ethereum, etherscan, https://example.com',
      );
    });
  });

  describe('expanding the message', () => {
    it('should offer no arrow while the message fits', () => {
      set(height, NOTIFICATION_MAX_HEIGHT);

      const { messageWrapperStyle, showExpandArrow } = card();

      expect(get(showExpandArrow)).toBe(false);
      expect(get(messageWrapperStyle)).toEqual({});
    });

    it('should offer the arrow once the message overflows', () => {
      set(height, NOTIFICATION_MAX_HEIGHT + 1);

      const { messageWrapperStyle, showExpandArrow } = card();

      expect(get(showExpandArrow)).toBe(true);
      expect(get(messageWrapperStyle)).toEqual({ height: `${NOTIFICATION_MAX_HEIGHT}px` });
    });

    it('should give the wrapper the full height once expanded', () => {
      set(height, 200);

      const { buttonClicked, messageWrapperStyle } = card();
      buttonClicked();

      expect(get(messageWrapperStyle)).toEqual({ height: '224px' });
    });

    it('should expand when the collapsed message is clicked', () => {
      set(height, 200);

      const { expanded, messageClicked } = card();
      messageClicked();

      expect(get(expanded)).toBe(true);
    });

    it('should stay expanded when a message that fits is clicked again', () => {
      const { expanded, messageClicked } = card();
      messageClicked();
      messageClicked();

      expect(get(expanded)).toBe(true);
    });

    it('should toggle back to collapsed from the button', () => {
      set(height, 200);

      const { buttonClicked, expanded } = card();
      buttonClicked();
      buttonClicked();

      expect(get(expanded)).toBe(false);
    });
  });
});
