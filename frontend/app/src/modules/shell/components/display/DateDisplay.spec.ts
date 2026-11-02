import { createCustomPinia } from '@test/utils/create-pinia';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

describe('dateDisplay', () => {
  it('should render a calendar date without a synthetic time or timezone shift', () => {
    const wrapper = mount(DateDisplay, {
      props: {
        calendarDate: '2026-11-02',
        milliseconds: true,
        noTime: true,
        timestamp: Date.UTC(2030, 0, 1),
      },
      global: {
        plugins: [createCustomPinia()],
        stubs: {
          CopyTooltip: { template: '<span><slot /></span>' },
        },
      },
    });

    expect(wrapper.text()).toContain('02/11/2026');
    expect(wrapper.text()).not.toContain(':');
  });

  it('should not expose the source calendar date while timestamps are scrambled', () => {
    const pinia = createCustomPinia();
    useSettingsRepo(pinia).updateFrontend({ scrambleData: true, scrambleMultiplier: 1 });
    const wrapper = mount(DateDisplay, {
      props: {
        calendarDate: '2026-11-02',
        milliseconds: true,
        noTime: true,
        timestamp: Date.UTC(2030, 0, 1),
      },
      global: {
        plugins: [pinia],
        stubs: {
          CopyTooltip: { template: '<span><slot /></span>' },
        },
      },
    });

    expect(wrapper.text()).not.toContain('2026');
  });
});
