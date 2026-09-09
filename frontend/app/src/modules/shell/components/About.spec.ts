import type { SystemVersion } from '@shared/ipc';
import type { WebVersion } from '@/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick, type Ref } from 'vue';
import About from '@/modules/shell/components/About.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { copy, dataDirectory, getVersion, premium, version, versionSource } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    copy: vi.fn(),
    dataDirectory: ref<string>('/home/user/.local/share/rotki/data'),
    getVersion: vi.fn(),
    premium: ref<boolean>(false),
    version: ref<{ version: string }>({ version: '1.45.0' }),
    versionSource: ref<string>(''),
  };
});

vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: (): { dataDirectory: Ref<string>; version: Ref<{ version: string }> } => ({
    dataDirectory,
    version,
  }),
}));

vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: (): Ref<boolean> => premium,
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): Record<string, unknown> => ({
    isPackaged: true,
    openPath: vi.fn(),
    version: getVersion,
  }),
}));

vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual<typeof import('@vueuse/core')>('@vueuse/core');
  return {
    ...actual,
    useClipboard: (options: { source: Ref<string> }): { copy: Mock } => {
      set(versionSource, get(options.source));
      return { copy };
    },
  };
});

const electron: SystemVersion = { arch: 'x64', electron: '43.5.0', os: 'Linux', osVersion: '6.1' };
const web: WebVersion = { platform: 'Linux x86_64', userAgent: 'Mozilla/5.0 rotki' };

function createWrapper(): VueWrapper<any> {
  return mount(About, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        AboutDataDirectory: true,
        AppUpdateIndicator: true,
        DateDisplay: { name: 'DateDisplay', props: ['timestamp'], template: '<span />' },
        ExternalLink: true,
        RotkiLogo: true,
      },
    },
  });
}

/** `asyncComputed` resolves after mount, so the platform rows need a tick to appear. */
async function mountResolved(): Promise<VueWrapper<any>> {
  const wrapper = createWrapper();
  await nextTick();
  await nextTick();
  return wrapper;
}

describe('about', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(premium, false);
    getVersion.mockResolvedValue(electron);
    window.PremiumComponents = undefined;
  });

  afterEach(() => {
    window.PremiumComponents = undefined;
  });

  /**
   * The same endpoint answers with either shape, and only one of the two platform blocks belongs
   * on screen: a browser has no electron build to report, and a desktop build has no user agent
   * worth showing.
   */
  describe('which platform it reports', () => {
    it('should show the electron build on the desktop app', async () => {
      const wrapper = await mountResolved();

      expect(wrapper.find('[data-testid=about-electron-version]').text()).toContain('43.5.0');
      expect(wrapper.find('[data-testid=about-electron-platform]').text()).toContain('Linux x64 6.1');
      expect(wrapper.find('[data-testid=about-user-agent]').exists()).toBe(false);
    });

    it('should show the user agent in a browser', async () => {
      getVersion.mockResolvedValue(web);

      const wrapper = await mountResolved();

      expect(wrapper.find('[data-testid=about-user-agent]').text()).toContain('Mozilla/5.0 rotki');
      expect(wrapper.find('[data-testid=about-web-platform]').text()).toContain('Linux x86_64');
      expect(wrapper.find('[data-testid=about-electron-version]').exists()).toBe(false);
    });

    it('should show neither until the version resolves', () => {
      const wrapper = createWrapper();

      expect(wrapper.find('[data-testid=about-electron-version]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=about-user-agent]').exists()).toBe(false);
    });
  });

  /**
   * The premium components load into the page at runtime, so they are reported only when premium
   * is active and the bundle actually arrived.
   */
  describe('the premium components', () => {
    it('should be reported once premium loaded them', async () => {
      set(premium, true);
      window.PremiumComponents = { build: 1_700_000_000_000, version: '16.0.1' };

      const wrapper = await mountResolved();

      expect(wrapper.find('[data-testid=about-components-version]').text()).toContain('16.0.1');
    });

    it('should be left out for a non-premium account', async () => {
      window.PremiumComponents = { build: 1_700_000_000_000, version: '16.0.1' };

      const wrapper = await mountResolved();

      expect(wrapper.find('[data-testid=about-components-version]').exists()).toBe(false);
    });

    it('should be left out when premium is on but the bundle never arrived', async () => {
      set(premium, true);

      const wrapper = await mountResolved();

      expect(wrapper.find('[data-testid=about-components-version]').exists()).toBe(false);
    });

    it('should report the build as a date rather than a timestamp', async () => {
      set(premium, true);
      window.PremiumComponents = { build: 1_700_000_000_000, version: '16.0.1' };

      const wrapper = await mountResolved();

      expect(wrapper.findComponent({ name: 'DateDisplay' }).props('timestamp')).toBe(1_700_000_000);
    });

    /** A zero build time is the bundle saying it does not know, not midnight in 1970. */
    it('should skip a build time the bundle could not report', async () => {
      set(premium, true);
      window.PremiumComponents = { build: 0, version: '16.0.1' };

      const wrapper = await mountResolved();

      expect(wrapper.find('[data-testid=about-components-build]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=about-components-version]').exists()).toBe(true);
    });
  });

  /** The whole point of the screen is pasting the versions into a bug report. */
  describe('copying', () => {
    it('should copy on request', async () => {
      const wrapper = await mountResolved();

      await wrapper.find('[data-testid=about-copy]').trigger('click');

      expect(copy).toHaveBeenCalledTimes(1);
    });

    it('should copy the assembled version text rather than the raw versions', async () => {
      await mountResolved();

      expect(get(versionSource)).toContain('1.45.0');
    });
  });
});
