import { NotificationCategory, type NotificationData, Severity } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { storeToRefs } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import NotificationSidebar from '@/modules/core/notifications/NotificationSidebar.vue';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';

interface MockedDependencies {
  isActive?: Ref<boolean>;
  silent?: Ref<boolean>;
}

const { deps, toggleSilent } = vi.hoisted(() => {
  const deps: MockedDependencies = {};
  return { deps, toggleSilent: vi.fn(async () => Promise.resolve()) };
});

let isActive: Ref<boolean>;
let silent: Ref<boolean>;

vi.mock('@/modules/core/notifications/use-notification-cooldown', () => ({
  useNotificationCooldown: vi.fn(() => ({
    recordDisplay: vi.fn(),
    resetSchedule: vi.fn(),
    shouldSuppress: vi.fn(() => false),
  })),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ isActive: deps.isActive }),
}));

vi.mock('@/modules/core/notifications/use-silent-notifications', () => ({
  useSilentNotifications: (): Record<string, unknown> => ({
    silent: deps.silent,
    toggle: toggleSilent,
  }),
}));

function notification(overrides: Partial<NotificationData> = {}): NotificationData {
  return {
    category: NotificationCategory.DEFAULT,
    date: new Date('2026-03-04T05:06:07Z'),
    display: true,
    duration: 5000,
    id: 1,
    message: 'the message',
    severity: Severity.INFO,
    title: 'the title',
    ...overrides,
  };
}

const passThrough = { template: '<div><slot /></div>' };

function createWrapper(notifications: NotificationData[] = []): VueWrapper {
  const pinia = createCustomPinia();
  const wrapper = mount(NotificationSidebar, {
    global: {
      plugins: [pinia],
      stubs: {
        LazyLoader: passThrough,
        PendingTasks: true,
        RouterLink: passThrough,
        RuiNavigationDrawer: passThrough,
      },
    },
    props: { modelValue: true },
  });
  set(storeToRefs(useNotificationsStore(pinia)).data, notifications);
  return wrapper;
}

describe('modules/core/notifications/NotificationSidebar.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    isActive = ref<boolean>(false);
    silent = ref<boolean>(false);
    deps.isActive = isActive;
    deps.silent = silent;
  });

  it('should render one card per notification', async () => {
    const wrapper = createWrapper([notification({ id: 1 }), notification({ id: 2 })]);
    await nextTick();

    expect(wrapper.findAll('[data-id=notification]')).toHaveLength(2);
  });

  it('should dismiss the notification a card asks it to, and only that one', async () => {
    const wrapper = createWrapper([
      notification({ id: 1, title: 'first' }),
      notification({ id: 2, title: 'second' }),
    ]);
    await nextTick();

    const cards = wrapper.findAll('[data-id=notification]');
    const dismissFirst = cards.find(card => card.text().includes('first'))!;
    await dismissFirst.find('[data-id=notification_dismiss]').trigger('click');
    await nextTick();

    const remaining = wrapper.findAll('[data-id=notification]');
    expect(remaining).toHaveLength(1);
    expect(remaining[0].text()).toContain('second');
  });

  it('should offer nothing to clear while the list is empty', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=clear-notifications]').attributes('disabled')).toBeDefined();
  });

  it('should allow clearing once there is something to clear', async () => {
    const wrapper = createWrapper([notification()]);
    await nextTick();

    expect(wrapper.find('[data-testid=clear-notifications]').attributes('disabled')).toBeUndefined();
  });

  it('should toggle silent mode from its button', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=silent-notifications-toggle]').trigger('click');

    expect(toggleSilent).toHaveBeenCalledOnce();
  });

  it('should close the drawer when asked', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=close-notifications]').trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
  });
});
