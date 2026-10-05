import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useReportIssue } from '@/modules/core/common/use-report-issue';
import ReportIssueDialog from './ReportIssueDialog.vue';

/**
 * The seam: the dialog may close and drop the user's title and description only once
 * the target app or form accepted them. `openUrl` rejecting (no mail client, or the
 * main process refusing the url) has to leave the dialog open with the draft intact.
 */

const { mockOpenUrl } = vi.hoisted(() => ({
  mockOpenUrl: vi.fn<(url: string) => Promise<void>>(),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => ({
    openUrl: mockOpenUrl,
  })),
}));

describe('modules/shell/components/ReportIssueDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof ReportIssueDialog>> | undefined;

  function createWrapper(): VueWrapper<InstanceType<typeof ReportIssueDialog>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    useReportIssue().show({ title: 'Balances missing', description: 'Steps to reproduce' });
    return mount(ReportIssueDialog, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiDialog: { template: '<div v-if="modelValue"><slot /></div>', props: ['modelValue'] },
        },
      },
    });
  }

  async function clickEmail(): Promise<void> {
    assert(wrapper);
    // The draft is copied in on mount, so the buttons enable one render later.
    await nextTick();
    await wrapper.find('[data-testid=submit-email]').trigger('click');
    await flushPromises();
  }

  beforeEach(() => {
    mockOpenUrl.mockReset();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should close the dialog once the mail client opened', async () => {
    mockOpenUrl.mockResolvedValue(undefined);
    wrapper = createWrapper();

    await clickEmail();

    expect(mockOpenUrl).toHaveBeenCalledWith(expect.stringMatching(/^mailto:.*subject=Balances%20missing/));
    expect(get(useReportIssue().visible)).toBe(false);
  });

  it('should keep the dialog and the draft when the mail client fails to open', async () => {
    mockOpenUrl.mockRejectedValue(new Error('Requested to open untrusted URL'));
    wrapper = createWrapper();

    await clickEmail();

    expect(get(useReportIssue().visible)).toBe(true);
    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('Balances missing');
    expect(wrapper.find<HTMLTextAreaElement>('textarea').element.value).toBe('Steps to reproduce');
    expect(wrapper.find('[data-testid=report-issue-open-error]').exists()).toBe(true);
  });
});
