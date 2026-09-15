import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HistoryQueryIndicatorSettings from '@/modules/settings/interface/HistoryQueryIndicatorSettings.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { resetQueryStatus } = vi.hoisted(() => ({ resetQueryStatus: vi.fn<() => void>() }));

vi.mock('@/modules/history/sync-status/use-history-sync-status', () => ({
  useHistorySyncStatus: (): object => ({ resetQueryStatus }),
}));

const SUCCESS_TEXT = 'frontend_settings.history_query_indicator.reset_dismissal_status.success';

function createWrapper(): VueWrapper {
  return mount(HistoryQueryIndicatorSettings, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        HistoryQueryIndicatorDismissalThresholdSetting: true,
        HistoryQueryIndicatorMinOutOfSyncPeriodSetting: true,
        SettingCategory: { template: '<div><slot name="title" /><slot /></div>' },
        SettingsItem: { template: '<div><slot name="title" /><slot name="subtitle" /><slot /></div>' },
      },
    },
  });
}

describe('modules/settings/interface/HistoryQueryIndicatorSettings', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetQueryStatus.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should clear the history sync dismissal and confirm it, holding the button until the notice goes', async () => {
    const wrapper = createWrapper();
    const button = wrapper.find('[data-testid=history-query-indicator-reset]');

    await button.trigger('click');

    expect(resetQueryStatus).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain(SUCCESS_TEXT);
    expect(button.attributes('disabled')).toBeDefined();

    await vi.advanceTimersByTimeAsync(5000);

    expect(wrapper.text()).not.toContain(SUCCESS_TEXT);
    expect(button.attributes('disabled')).toBeUndefined();
  });
});
