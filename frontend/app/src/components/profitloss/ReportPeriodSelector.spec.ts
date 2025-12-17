import type { PeriodChangedEvent, SelectionChangedEvent } from '@/types/reports';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import ReportPeriodSelector from '@/components/profitloss/ReportPeriodSelector.vue';
import { Quarter } from '@/types/settings/frontend-settings';
import { setupDayjs } from '@/utils/date';

describe('components/profitloss/ReportPeriodSelector.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof ReportPeriodSelector>>;
  let pinia: Pinia;

  const currentYear = new Date().getFullYear().toString();

  beforeAll(() => {
    setupDayjs();
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (
    options: ComponentMountingOptions<typeof ReportPeriodSelector> = {
      props: {
        quarter: Quarter.ALL,
        year: currentYear,
      },
    },
  ): VueWrapper<InstanceType<typeof ReportPeriodSelector>> =>
    mount(ReportPeriodSelector, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiIcon: true,
        },
      },
      ...options,
    });

  describe('year selection', () => {
    it('should render year buttons for the last 5 years', () => {
      wrapper = createWrapper();

      const yearButtons = wrapper.findAll('[data-cy=button-group-report-period-year] button');

      const expectedYears: string[] = [];
      for (let i = 0; i < 5; i++) {
        expectedYears.push((Number(currentYear) - i).toString());
      }

      expect(yearButtons).toHaveLength(5);
      expectedYears.forEach((year, index) => {
        expect(yearButtons[index].text()).toBe(year);
      });
    });

    it('should emit update:selection when a year button is clicked', async () => {
      wrapper = createWrapper();

      const yearButtons = wrapper.findAll('[data-cy=button-group-report-period-year] button');
      const previousYear = (Number(currentYear) - 1).toString();

      await yearButtons[1].trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const selectionEvents = wrapper.emitted('update:selection') as SelectionChangedEvent[][];
      expect(selectionEvents).toBeTruthy();
      expect(selectionEvents.at(-1)![0]).toMatchObject({
        quarter: Quarter.ALL,
        year: previousYear,
      });
    });

    it('should emit update:period with correct timestamps when year is selected', async () => {
      wrapper = createWrapper();

      const yearButtons = wrapper.findAll('[data-cy=button-group-report-period-year] button');

      await yearButtons[1].trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const periodEvents = wrapper.emitted('update:period') as PeriodChangedEvent[][];
      expect(periodEvents).toBeTruthy();

      const lastPeriodEvent = periodEvents.at(-1)![0];
      expect(lastPeriodEvent).not.toBeNull();
      expect(lastPeriodEvent.start).toBeGreaterThan(0);
      expect(lastPeriodEvent.end).toBeGreaterThan(lastPeriodEvent.start);
    });
  });

  describe('older years dropdown', () => {
    it('should not change yearModel when dropdown button is clicked', async () => {
      wrapper = createWrapper();

      const dropdownButton = wrapper.find('[data-cy=button-older-years]');
      expect(dropdownButton.exists()).toBe(true);

      const initialSelectionEvents = wrapper.emitted('update:selection');
      const initialCount = initialSelectionEvents?.length ?? 0;

      await dropdownButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const selectionEventsAfterClick = wrapper.emitted('update:selection');
      const afterCount = selectionEventsAfterClick?.length ?? 0;

      expect(afterCount).toBe(initialCount);
    });

    it('should display selected older year in dropdown button', () => {
      const olderYear = (Number(currentYear) - 6).toString();
      wrapper = createWrapper({
        props: {
          quarter: Quarter.ALL,
          year: olderYear,
        },
      });

      const dropdownButton = wrapper.find('[data-cy=button-older-years]');
      expect(dropdownButton.text()).toContain(olderYear);
    });
  });

  describe('all-time selection', () => {
    it('should emit correct events when all-time is clicked', async () => {
      wrapper = createWrapper();

      const allTimeButton = wrapper.find('[data-cy=button-all-time]');
      expect(allTimeButton.exists()).toBe(true);

      await allTimeButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const selectionEvents = wrapper.emitted('update:selection') as SelectionChangedEvent[][];
      expect(selectionEvents).toBeTruthy();
      expect(selectionEvents.at(-1)![0]).toMatchObject({
        quarter: Quarter.ALL,
        year: 'all-time',
      });

      const periodEvents = wrapper.emitted('update:period') as PeriodChangedEvent[][];
      expect(periodEvents).toBeTruthy();
      const lastPeriodEvent = periodEvents.at(-1)![0];
      expect(lastPeriodEvent.start).toBe(0);
      expect(lastPeriodEvent.end).toBeLessThanOrEqual(dayjs().unix());
    });
  });

  describe('custom selection', () => {
    it('should emit update:selection with custom year when custom is clicked', async () => {
      wrapper = createWrapper();

      const customButton = wrapper.find('[data-cy=button-custom]');
      expect(customButton.exists()).toBe(true);

      await customButton.trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const selectionEvents = wrapper.emitted('update:selection') as SelectionChangedEvent[][];
      expect(selectionEvents).toBeTruthy();
      expect(selectionEvents.at(-1)![0]).toMatchObject({
        year: 'custom',
      });
    });

    it('should not show quarter selection when custom is selected', () => {
      wrapper = createWrapper({
        props: {
          quarter: Quarter.ALL,
          year: 'custom',
        },
      });

      const quarterButtonGroup = wrapper.find('[data-cy=button-group-quarter]');
      expect(quarterButtonGroup.exists()).toBe(false);
    });
  });

  describe('quarter selection', () => {
    it('should show quarter buttons when a year is selected', () => {
      wrapper = createWrapper({
        props: {
          quarter: Quarter.ALL,
          year: currentYear,
        },
      });

      const quarterButtonGroup = wrapper.find('[data-cy=button-group-quarter]');
      expect(quarterButtonGroup.exists()).toBe(true);

      const quarterButtons = quarterButtonGroup.findAll('button');
      expect(quarterButtons).toHaveLength(5);
    });

    it('should not show quarter buttons when all-time is selected', () => {
      wrapper = createWrapper({
        props: {
          quarter: Quarter.ALL,
          year: 'all-time',
        },
      });

      const quarterButtonGroup = wrapper.find('[data-cy=button-group-quarter]');
      expect(quarterButtonGroup.exists()).toBe(false);
    });

    it('should emit update:selection when a quarter is selected', async () => {
      wrapper = createWrapper({
        props: {
          quarter: Quarter.ALL,
          year: currentYear,
        },
      });

      const quarterButtonGroup = wrapper.find('[data-cy=button-group-quarter]');
      const quarterButtons = quarterButtonGroup.findAll('button');

      await quarterButtons[1].trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const selectionEvents = wrapper.emitted('update:selection') as SelectionChangedEvent[][];
      expect(selectionEvents).toBeTruthy();
      expect(selectionEvents.at(-1)![0]).toMatchObject({
        quarter: Quarter.Q1,
        year: currentYear,
      });
    });
  });

  describe('period calculation', () => {
    it('should emit correct period on mount', async () => {
      wrapper = createWrapper({
        props: {
          quarter: Quarter.ALL,
          year: currentYear,
        },
      });

      await vi.advanceTimersToNextTimerAsync();

      const periodEvents = wrapper.emitted('update:period') as PeriodChangedEvent[][];
      expect(periodEvents).toBeTruthy();
      expect(periodEvents.length).toBeGreaterThan(0);

      const firstPeriodEvent = periodEvents[0][0];
      expect(firstPeriodEvent).not.toBeNull();
    });

    it('should emit null period when switching to custom', async () => {
      wrapper = createWrapper({
        props: {
          quarter: Quarter.ALL,
          year: currentYear,
        },
      });

      await vi.advanceTimersToNextTimerAsync();

      await wrapper.setProps({ year: 'custom' });
      await vi.advanceTimersToNextTimerAsync();

      const periodEvents = wrapper.emitted('update:period') as (PeriodChangedEvent | null)[][];
      const lastEvent = periodEvents.at(-1)![0];
      expect(lastEvent).toBeNull();
    });
  });
});
