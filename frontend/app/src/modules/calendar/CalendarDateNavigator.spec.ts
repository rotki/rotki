import { mount, type VueWrapper } from '@vue/test-utils';
import dayjs, { type Dayjs } from 'dayjs';
import { describe, expect, it } from 'vitest';
import CalendarDateNavigator from '@/modules/calendar/CalendarDateNavigator.vue';
import '@test/i18n';

const TODAY = dayjs('2026-10-31');

function createWrapper(selected: Dayjs, visibleDate: Dayjs): VueWrapper {
  return mount(CalendarDateNavigator, {
    props: { modelValue: selected, today: TODAY, visibleDate },
    global: {
      stubs: {
        DateTimePicker: true,
        RuiButton: { props: ['disabled'], template: '<button :disabled="disabled"><slot /></button>' },
        RuiIcon: true,
        RuiMenu: true,
      },
    },
  });
}

function isTodayDisabled(wrapper: VueWrapper): boolean {
  return wrapper.find('[data-testid=calendar-today]').attributes('disabled') !== undefined;
}

describe('calendarDateNavigator', () => {
  it('should disable Today while today is selected in the current month', () => {
    expect(isTodayDisabled(createWrapper(TODAY, TODAY))).toBe(true);
  });

  it('should keep Today disabled after month navigation moved the visible day off the 31st', () => {
    const visibleDate = TODAY.add(1, 'month').subtract(1, 'month');

    expect(isTodayDisabled(createWrapper(TODAY, visibleDate))).toBe(true);
  });

  it('should enable Today while another month is visible', () => {
    expect(isTodayDisabled(createWrapper(TODAY, TODAY.add(1, 'month')))).toBe(false);
  });

  it('should enable Today while another day is selected', () => {
    const selected = TODAY.subtract(3, 'day');

    expect(isTodayDisabled(createWrapper(selected, selected))).toBe(false);
  });
});
