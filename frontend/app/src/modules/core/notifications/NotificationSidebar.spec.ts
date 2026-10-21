import { type NotificationData, NotificationKind, Severity } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { storeToRefs } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import NotificationSidebar from '@/modules/core/notifications/NotificationSidebar.vue';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';

interface MockedDependencies {
  silent?: Ref<boolean>;
}

const { deps, toggleSilent } = vi.hoisted(() => {
  const deps: MockedDependencies = {};
  return { deps, toggleSilent: vi.fn(async () => Promise.resolve()) };
});

let silent: Ref<boolean>;

vi.mock('@/modules/core/notifications/use-notification-cooldown', () => ({
  useNotificationCooldown: vi.fn(() => ({
    recordDisplay: vi.fn(),
    resetSchedule: vi.fn(),
    shouldSuppress: vi.fn(() => false),
  })),
}));

vi.mock('@/modules/core/notifications/use-silent-notifications', () => ({
  useSilentNotifications: (): Record<string, unknown> => ({
    silent: deps.silent,
    toggle: toggleSilent,
  }),
}));

function notification(overrides: Partial<NotificationData> = {}): NotificationData {
  return {
    date: new Date('2026-03-04T05:06:07Z'),
    display: true,
    duration: 5000,
    id: 1,
    kind: NotificationKind.RESULT,
    message: 'the message',
    read: false,
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
    silent = ref<boolean>(false);
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

  describe('the history and the problems section', () => {
    it('should head the history by day', async () => {
      const wrapper = createWrapper([notification({ date: new Date(), id: 1 })]);
      await nextTick();

      expect(wrapper.findAll('[data-testid=notification-day]').map(day => day.text())).toEqual(['notification_sidebar.day.today']);
    });

    it('should file a failure under the problems, not in the history', async () => {
      const wrapper = createWrapper([notification({ id: 1, kind: NotificationKind.FAILURE, title: 'a failure' })]);
      await nextTick();

      expect(wrapper.findAll('[data-testid=notification-day]')).toHaveLength(0);
      expect(wrapper.find('[data-testid=notification-problems]').text()).toContain('a failure');
    });

    it('should hide what the problems section holds once it is folded', async () => {
      const wrapper = createWrapper([notification({ id: 1, kind: NotificationKind.FAILURE })]);
      await nextTick();

      await wrapper.find('[data-testid=notification-problems-toggle]').trigger('click');

      expect(wrapper.find('[data-testid=notification-problems]').findAll('[data-id=notification]')).toHaveLength(0);
      expect(wrapper.find('[data-testid=notification-problems-toggle]').attributes('aria-expanded')).toBe('false');
    });
  });

  describe('backend problems', () => {
    function fileProblem(subject: string): void {
      useBackendProblemsStore().record({
        at: new Date('2026-03-04T05:06:07Z'),
        count: 1,
        identity: 'tag',
        source: { fields: { entry: 'tag' }, group: ['error', 'local_db', subject, 'tag'], key: 'local_db', subject, value: 'Could not read a tag', verbosity: 'error' },
      });
    }

    it('should render one collapsed card per problem', async () => {
      const wrapper = createWrapper();
      fileProblem('kraken');
      fileProblem('binance');
      await nextTick();

      expect(wrapper.findAll('[data-testid=backend-problem]')).toHaveLength(2);
      expect(wrapper.findAll('[data-testid=backend-problem-item]')).toHaveLength(0);
    });

    it('should show the items of a problem once expanded', async () => {
      const wrapper = createWrapper();
      fileProblem('kraken');
      await nextTick();

      await wrapper.find('[data-testid=backend-problem-toggle]').trigger('click');

      expect(wrapper.findAll('[data-testid=backend-problem-item]')).toHaveLength(1);
    });

    it('should dismiss the problem a card asks it to', async () => {
      const wrapper = createWrapper();
      fileProblem('kraken');
      await nextTick();

      await wrapper.find('[data-testid=backend-problem-dismiss]').trigger('click');

      expect(wrapper.findAll('[data-testid=backend-problem]')).toHaveLength(0);
      expect(get(storeToRefs(useBackendProblemsStore()).problems)).toEqual([]);
    });

    it('should close the drawer once an item action runs', async () => {
      const wrapper = createWrapper();
      fileProblem('kraken');
      await nextTick();

      await wrapper.find('[data-testid=backend-problem-toggle]').trigger('click');
      await wrapper.find('[data-testid=backend-problem-item-action]').trigger('click');

      expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
    });

    it('should offer clearing and leave the caught-up state when only a problem is filed', async () => {
      const wrapper = createWrapper();
      fileProblem('kraken');
      await nextTick();

      expect(wrapper.find('[data-testid=clear-notifications]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=notifications-empty]').exists()).toBe(false);
    });
  });

  it('should show the caught-up state and nothing to clear while the list is empty', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=clear-notifications]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=notifications-empty]').text()).toContain('notification_sidebar.empty.title');
  });

  it('should allow clearing once there is something to clear', async () => {
    const wrapper = createWrapper([notification()]);
    await nextTick();

    expect(wrapper.find('[data-testid=clear-notifications]').attributes('disabled')).toBeUndefined();
    expect(wrapper.find('[data-testid=notifications-empty]').exists()).toBe(false);
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
