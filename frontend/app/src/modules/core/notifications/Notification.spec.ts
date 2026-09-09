import { type NotificationAction, NotificationCategory, type NotificationData, Severity } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import Notification from '@/modules/core/notifications/Notification.vue';

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

function createWrapper(data: NotificationData = notification()): VueWrapper {
  return mount(Notification, {
    props: { notification: data },
  });
}

describe('modules/core/notifications/Notification.vue', () => {
  it('should show the title and the message', () => {
    const wrapper = createWrapper(notification({ message: 'disk is full', title: 'Backup failed' }));

    expect(wrapper.text()).toContain('Backup failed');
    expect(wrapper.text()).toContain('disk is full');
  });

  it('should emit the notification id when dismissed', async () => {
    const wrapper = createWrapper(notification({ id: 11 }));

    await wrapper.find('[data-id=notification_dismiss]').trigger('click');

    expect(wrapper.emitted('dismiss')).toEqual([[11]]);
  });

  it('should render one button per action', () => {
    const actions: NotificationAction[] = [
      { action: vi.fn(), label: 'Retry' },
      { action: vi.fn(), label: 'Ignore' },
    ];

    const wrapper = createWrapper(notification({ action: actions }));

    expect(wrapper.text()).toContain('Retry');
    expect(wrapper.text()).toContain('Ignore');
  });

  it('should run the action and emit a dismissal when its button is pressed', async () => {
    const action = vi.fn();

    const wrapper = createWrapper(notification({ action: { action, label: 'Retry' }, id: 3 }));
    const button = wrapper.findAll('button').find(item => item.text().includes('Retry'));
    await button?.trigger('click');

    expect(action).toHaveBeenCalledOnce();
    expect(wrapper.emitted('dismiss')).toEqual([[3]]);
  });

  it('should offer a copy button only for an error', () => {
    const error = createWrapper(notification({ severity: Severity.ERROR }));
    const info = createWrapper(notification({ severity: Severity.INFO }));

    expect(error.text()).toContain('common.actions.copy');
    expect(info.text()).not.toContain('common.actions.copy');
  });

  it('should render the missing key notice instead of the raw message', () => {
    const wrapper = createWrapper(notification({
      i18nParam: {
        choice: 1,
        message: 'notification_messages.missing_api_key',
        props: { location: 'ethereum', service: 'etherscan', url: 'https://example.com' },
      },
      message: 'the untranslated message',
    }));

    expect(wrapper.text()).not.toContain('the untranslated message');
  });
});
