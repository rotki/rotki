import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CalendarView from '@/modules/calendar/CalendarView.vue';
import '@test/i18n';

const { error, fetchData } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return { error: shallowRef<Error | undefined>(), fetchData: vi.fn<() => Promise<void>>() };
});

vi.mock('vue-router', () => ({
  useRoute: (): unknown => ({ query: {} }),
  useRouter: (): unknown => ({ replace: vi.fn() }),
}));

vi.mock('@/modules/calendar/use-calendar-data', async () => {
  const { computed, ref } = await import('vue');
  return {
    useCalendarData: (): Record<string, unknown> => ({
      dateFormat: computed<string>(() => 'YYYY-MM-DD'),
      error,
      eventsWithDate: computed<unknown[]>(() => []),
      fetchData,
      initializePagination: vi.fn(),
      isLoading: ref<boolean>(false),
      modelRange: ref({}),
      setToday: vi.fn(),
      today: ref(undefined),
      upcomingEvents: computed<unknown[]>(() => []),
    }),
  };
});

vi.mock('@/modules/calendar/use-calendar-date-management', async () => {
  const { computed, ref } = await import('vue');
  return {
    useCalendarDateManagement: (): Record<string, unknown> => ({
      modelSelectedDate: ref(undefined),
      modelVisibleDate: ref(undefined),
      selectedDateEvents: computed<unknown[]>(() => []),
      setSelectedDate: vi.fn(),
    }),
  };
});

vi.mock('@/modules/calendar/use-calendar-operations', async () => {
  const { ref } = await import('vue');
  return {
    useCalendarOperations: (): Record<string, unknown> => ({
      add: vi.fn(),
      deleteEvent: vi.fn(),
      edit: vi.fn(),
      editMode: ref<boolean>(false),
      modelValue: ref(undefined),
    }),
  };
});

function createWrapper(): VueWrapper {
  return mount(CalendarView, {
    global: {
      stubs: {
        BlockchainAccountSelector: true,
        CalendarDateNavigator: true,
        CalendarFormDialog: true,
        CalendarGrid: true,
        CalendarMonthNavigator: true,
        CalendarSelectedEventsPanel: true,
        CalendarSettingsMenu: true,
        CalendarUpcomingEventsPanel: true,
        RuiButton: true,
        RuiIcon: true,
        TableFrame: { template: '<div><slot /></div>' },
        TablePageLayout: { template: '<div><slot /></div>' },
      },
    },
  });
}

describe('calendarView', () => {
  beforeEach(() => {
    set(error, undefined);
    fetchData.mockReset();
  });

  it('should say why the events could not be loaded above the calendar, and load them again from there', async () => {
    set(error, new Error('backend down'));
    const wrapper = createWrapper();

    const alert = wrapper.find('[data-testid=calendar-fetch-error]');
    expect(alert.text()).toContain('backend down');
    await alert.find('[data-testid=table-failure-strip-retry]').trigger('click');

    expect(fetchData).toHaveBeenCalledOnce();
  });

  it('should show no alert while nothing failed', () => {
    expect(createWrapper().find('[data-testid=calendar-fetch-error]').exists()).toBe(false);
  });
});
