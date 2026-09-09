import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import HelpSidebar from '@/modules/shell/components/HelpSidebar.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { downloadFileByTextContent, getAll, interop, notify, showReportIssue } = vi.hoisted(() => ({
  downloadFileByTextContent: vi.fn(),
  getAll: vi.fn(),
  interop: { isPackaged: false, openUrl: vi.fn() },
  notify: vi.fn(),
  showReportIssue: vi.fn(),
}));

vi.mock('@/modules/core/common/file/download', () => ({
  downloadFileByTextContent,
}));

vi.mock('@/modules/core/common/helpers/indexed-db', () => ({
  IndexedDb: class {
    getAll = getAll;
  },
}));

vi.mock('@/modules/core/common/use-report-issue', () => ({
  useReportIssue: (): { show: Mock } => ({ show: showReportIssue }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): { notify: Mock } => ({ notify }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): typeof interop => interop,
}));

/** The drawer teleports, so a pass-through keeps its contents inside the wrapper. */
const DrawerStub = {
  name: 'RuiNavigationDrawer',
  props: ['modelValue', 'width', 'temporary', 'position'],
  template: '<div><slot /></div>',
};

function createWrapper(): VueWrapper<any> {
  return mount(HelpSidebar, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: { RuiNavigationDrawer: DrawerStub },
    },
    props: { modelValue: true },
  });
}

/** Runs the log download, invoking whatever the store handed back to its callback. */
async function downloadLog(wrapper: VueWrapper<any>, entries: unknown[]): Promise<void> {
  getAll.mockImplementation(async (callback: (data: unknown[]) => void) => {
    callback(entries);
  });
  await wrapper.find('[data-testid=help-download-log]').trigger('click');
}

describe('helpSidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    interop.isPackaged = false;
  });

  it('should open the report issue dialog', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=help-report-issue]').trigger('click');

    expect(showReportIssue).toHaveBeenCalledTimes(1);
  });

  it('should close on request', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=help-close]').trigger('click');

    expect(wrapper.emitted<[boolean]>('update:modelValue')?.at(-1)?.[0]).toBe(false);
  });

  /** The about screen replaces the sidebar rather than opening behind it. */
  it('should close itself when opening the about screen', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=help-about]').trigger('click');

    expect(wrapper.emitted('about')).toHaveLength(1);
    expect(wrapper.emitted<[boolean]>('update:modelValue')?.at(-1)?.[0]).toBe(false);
  });

  /**
   * A packaged build has no browser to open a link in and no browser log to download, so it hands
   * the link to the desktop shell and drops the two browser-only rows.
   */
  describe('in a packaged build', () => {
    it('should open a link through the desktop shell rather than as an href', async () => {
      interop.isPackaged = true;
      const wrapper = createWrapper();

      const link = wrapper.findAll('[data-testid=help-link]')[0];
      await link.trigger('click');

      expect(interop.openUrl).toHaveBeenCalledTimes(1);
      expect(link.attributes('href')).toBeUndefined();
    });

    it('should leave the link to the browser otherwise', async () => {
      const wrapper = createWrapper();

      const link = wrapper.findAll('[data-testid=help-link]')[0];
      await link.trigger('click');

      expect(interop.openUrl).not.toHaveBeenCalled();
      expect(link.attributes('href')).toBeTruthy();
    });

    it('should withhold the about and log rows', () => {
      interop.isPackaged = true;

      const wrapper = createWrapper();

      expect(wrapper.find('[data-testid=help-about]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=help-download-log]').exists()).toBe(false);
    });
  });

  describe('downloading the browser log', () => {
    it('should download what the log holds', async () => {
      const wrapper = createWrapper();

      await downloadLog(wrapper, [{ message: 'first' }, { message: 'second' }]);

      expect(downloadFileByTextContent).toHaveBeenCalledWith('first\nsecond', 'frontend_log.txt');
    });

    /** An empty file would look like a successful download of nothing. */
    it('should say so rather than download an empty log', async () => {
      const wrapper = createWrapper();

      await downloadLog(wrapper, []);

      expect(downloadFileByTextContent).not.toHaveBeenCalled();
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        message: 'help_sidebar.browser_log.error.empty.message',
      }));
    });
  });
});
