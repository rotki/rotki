import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SponsorshipView from '@/components/sponsorship/SponsorshipView.vue';
import { useMainStore } from '@/store/main';

vi.mock('@/composables/electron-interop', () => ({
  useInterop: () => ({
    isPackaged: false,
    openUrl: vi.fn(),
  }),
}));

vi.mock('@/composables/links', () => ({
  useLinks: (url: { value: string }) => ({
    href: url,
    linkTarget: '_blank',
    onLinkClick: vi.fn(),
  }),
}));

describe('sponsorshipView.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof SponsorshipView>>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);

    localStorage.clear();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  function createWrapper(props: { drawer?: boolean } = {}) {
    return mount(SponsorshipView, {
      global: {
        plugins: [pinia],
        stubs: {
          AppImage: true,
          ExternalLink: true,
        },
      },
      props,
    });
  }

  it('should render the component', () => {
    wrapper = createWrapper();

    expect(wrapper.exists()).toBe(true);
  });

  it('should display version from store', () => {
    const store = useMainStore();
    const { version } = storeToRefs(store);
    set(version, {
      downloadUrl: '',
      latestVersion: '',
      version: '1.42.0',
    });

    wrapper = createWrapper();

    expect(wrapper.text()).toContain('1.42.0');
  });

  it('should display sponsor name', () => {
    wrapper = createWrapper();

    expect(wrapper.text()).toContain('jespow.eth');
  });

  it('should apply drawer-specific classes when drawer prop is true', () => {
    wrapper = createWrapper({ drawer: true });

    const appImage = wrapper.findComponent({ name: 'AppImage' });
    expect(appImage.classes()).toContain('size-20');
  });

  it('should apply non-drawer classes when drawer prop is false', () => {
    wrapper = createWrapper({ drawer: false });

    const appImage = wrapper.findComponent({ name: 'AppImage' });
    expect(appImage.classes()).toContain('size-24');
    expect(appImage.classes()).toContain('min-w-24');
  });

  it('should render external link for sponsorship', () => {
    wrapper = createWrapper();

    const externalLink = wrapper.findComponent({ name: 'ExternalLink' });
    expect(externalLink.exists()).toBe(true);
  });

  it('should display different sponsor images for login vs drawer', () => {
    localStorage.setItem('rotki.sponsorship.login_index', '0');

    const loginWrapper = createWrapper({ drawer: false });
    const loginAppImage = loginWrapper.findComponent({ name: 'AppImage' });
    const loginSrc = loginAppImage.attributes('src');

    loginWrapper.unmount();

    const drawerWrapper = createWrapper({ drawer: true });
    const drawerAppImage = drawerWrapper.findComponent({ name: 'AppImage' });
    const drawerSrc = drawerAppImage.attributes('src');

    expect(loginSrc).not.toBe(drawerSrc);

    drawerWrapper.unmount();
    wrapper = createWrapper();
  });

  it('should alternate sponsor on subsequent logins', () => {
    localStorage.setItem('rotki.sponsorship.login_index', '0');

    const wrapper1 = createWrapper({ drawer: false });
    const src1 = wrapper1.findComponent({ name: 'AppImage' }).attributes('src');
    wrapper1.unmount();

    const wrapper2 = createWrapper({ drawer: false });
    const src2 = wrapper2.findComponent({ name: 'AppImage' }).attributes('src');
    wrapper2.unmount();

    expect(src1).not.toBe(src2);

    wrapper = createWrapper();
  });

  describe('getCurrentSponsor logic', () => {
    const SPONSOR_1_IMAGE = '/assets/images/sponsorship/1.42.0_jespow.eth_1.png';
    const SPONSOR_2_IMAGE = '/assets/images/sponsorship/1.42.0_jespow.eth_2.png';

    describe('login screen (drawer=false)', () => {
      it('should set random index on first visit when loginIndex is -1', () => {
        localStorage.setItem('rotki.sponsorship.login_index', '-1');
        // Math.floor(0.3 * 2) = 0
        vi.spyOn(Math, 'random').mockReturnValue(0.3);

        wrapper = createWrapper({ drawer: false });

        const storedIndex = localStorage.getItem('rotki.sponsorship.login_index');
        expect(storedIndex).toBe('0');
        expect(wrapper.findComponent({ name: 'AppImage' }).attributes('src')).toBe(SPONSOR_1_IMAGE);

        vi.restoreAllMocks();
      });

      it('should set index to 1 when random produces index 1 on first visit', () => {
        localStorage.setItem('rotki.sponsorship.login_index', '-1');
        // Math.floor(0.7 * 2) = 1
        vi.spyOn(Math, 'random').mockReturnValue(0.7);

        wrapper = createWrapper({ drawer: false });

        const storedIndex = localStorage.getItem('rotki.sponsorship.login_index');
        expect(storedIndex).toBe('1');
        expect(wrapper.findComponent({ name: 'AppImage' }).attributes('src')).toBe(SPONSOR_2_IMAGE);

        vi.restoreAllMocks();
      });

      it('should cycle from 0 to 1 on subsequent login', () => {
        localStorage.setItem('rotki.sponsorship.login_index', '0');

        wrapper = createWrapper({ drawer: false });

        const storedIndex = localStorage.getItem('rotki.sponsorship.login_index');
        // (0 + 1) % 2 = 1
        expect(storedIndex).toBe('1');
        expect(wrapper.findComponent({ name: 'AppImage' }).attributes('src')).toBe(SPONSOR_2_IMAGE);
      });

      it('should cycle from 1 back to 0 on subsequent login (wrapping)', () => {
        localStorage.setItem('rotki.sponsorship.login_index', '1');

        wrapper = createWrapper({ drawer: false });

        const storedIndex = localStorage.getItem('rotki.sponsorship.login_index');
        // (1 + 1) % 2 = 0
        expect(storedIndex).toBe('0');
        expect(wrapper.findComponent({ name: 'AppImage' }).attributes('src')).toBe(SPONSOR_1_IMAGE);
      });

      it('should cycle correctly over multiple logins', () => {
        localStorage.setItem('rotki.sponsorship.login_index', '0');

        // First login: (0 + 1) % 2 = 1
        const wrapper1 = createWrapper({ drawer: false });
        expect(wrapper1.findComponent({ name: 'AppImage' }).attributes('src')).toBe(SPONSOR_2_IMAGE);
        wrapper1.unmount();

        // Second login: (1 + 1) % 2 = 0
        const wrapper2 = createWrapper({ drawer: false });
        expect(wrapper2.findComponent({ name: 'AppImage' }).attributes('src')).toBe(SPONSOR_1_IMAGE);
        wrapper2.unmount();

        // Third login: (0 + 1) % 2 = 1
        const wrapper3 = createWrapper({ drawer: false });
        expect(wrapper3.findComponent({ name: 'AppImage' }).attributes('src')).toBe(SPONSOR_2_IMAGE);
        wrapper3.unmount();

        wrapper = createWrapper();
      });
    });

    describe('drawer (drawer=true)', () => {
      it('should show next sponsor when loginIndex is 0', () => {
        localStorage.setItem('rotki.sponsorship.login_index', '0');

        wrapper = createWrapper({ drawer: true });

        // drawerIndex = (0 + 1) % 2 = 1
        expect(wrapper.findComponent({ name: 'AppImage' }).attributes('src')).toBe(SPONSOR_2_IMAGE);
        // Drawer should NOT modify loginIndex
        expect(localStorage.getItem('rotki.sponsorship.login_index')).toBe('0');
      });

      it('should show next sponsor (wrapping) when loginIndex is 1', () => {
        localStorage.setItem('rotki.sponsorship.login_index', '1');

        wrapper = createWrapper({ drawer: true });

        // drawerIndex = (1 + 1) % 2 = 0
        expect(wrapper.findComponent({ name: 'AppImage' }).attributes('src')).toBe(SPONSOR_1_IMAGE);
        // Drawer should NOT modify loginIndex
        expect(localStorage.getItem('rotki.sponsorship.login_index')).toBe('1');
      });

      it('should show different sponsor than login screen', () => {
        localStorage.setItem('rotki.sponsorship.login_index', '0');

        // Login screen: (0 + 1) % 2 = 1, shows sponsor 2
        const loginWrapper = createWrapper({ drawer: false });
        const loginSrc = loginWrapper.findComponent({ name: 'AppImage' }).attributes('src');
        loginWrapper.unmount();

        // Drawer: (1 + 1) % 2 = 0, shows sponsor 1
        const drawerWrapper = createWrapper({ drawer: true });
        const drawerSrc = drawerWrapper.findComponent({ name: 'AppImage' }).attributes('src');

        expect(loginSrc).toBe(SPONSOR_2_IMAGE);
        expect(drawerSrc).toBe(SPONSOR_1_IMAGE);
        expect(loginSrc).not.toBe(drawerSrc);

        drawerWrapper.unmount();
        wrapper = createWrapper();
      });
    });

    describe('login and drawer coordination', () => {
      it('should show different sponsors on login and drawer at the same time', () => {
        localStorage.setItem('rotki.sponsorship.login_index', '-1');
        // Math.floor(0.3 * 2) = 0
        vi.spyOn(Math, 'random').mockReturnValue(0.3);

        // First login sets index to 0, shows sponsor at index 0
        const loginWrapper = createWrapper({ drawer: false });
        const loginSrc = loginWrapper.findComponent({ name: 'AppImage' }).attributes('src');

        // Drawer shows (0 + 1) % 2 = 1
        const drawerWrapper = createWrapper({ drawer: true });
        const drawerSrc = drawerWrapper.findComponent({ name: 'AppImage' }).attributes('src');

        expect(loginSrc).toBe(SPONSOR_1_IMAGE);
        expect(drawerSrc).toBe(SPONSOR_2_IMAGE);

        loginWrapper.unmount();
        drawerWrapper.unmount();
        vi.restoreAllMocks();
        wrapper = createWrapper();
      });
    });

    describe('modular arithmetic for n sponsors', () => {
      it('should correctly wrap around using modulo', () => {
        // This tests the logic works for any number of sponsors
        // With 2 sponsors: indices cycle 0 -> 1 -> 0 -> 1 ...
        localStorage.setItem('rotki.sponsorship.login_index', '0');

        const indices: string[] = [];
        for (let i = 0; i < 4; i++) {
          const w = createWrapper({ drawer: false });
          indices.push(localStorage.getItem('rotki.sponsorship.login_index') ?? '');
          w.unmount();
        }

        // Should cycle: 1, 0, 1, 0
        expect(indices).toEqual(['1', '0', '1', '0']);

        wrapper = createWrapper();
      });
    });
  });
});
