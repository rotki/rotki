import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import SponsorshipView from '@/modules/premium/SponsorshipView.vue';

vi.mock('@/modules/shell/app/use-electron-interop', (): Record<string, unknown> => ({
  useInterop: (): { isPackaged: boolean; openUrl: ReturnType<typeof vi.fn> } => ({
    isPackaged: false,
    openUrl: vi.fn(),
  }),
}));

vi.mock('@/modules/shell/layout/use-links', (): Record<string, unknown> => ({
  useLinks: (
    url: { value: string },
  ): { href: { value: string }; linkTarget: string; onLinkClick: ReturnType<typeof vi.fn> } => ({
    href: url,
    linkTarget: '_blank',
    onLinkClick: vi.fn(),
  }),
}));

describe('sponsorship-view', () => {
  const SPONSOR_IMAGE = '/assets/images/sponsorship/1.43.0_pcaversaccio.jpg';
  const SPONSOR_NAME = 'pcaversaccio';

  let wrapper: VueWrapper<InstanceType<typeof SponsorshipView>>;
  let pinia: Pinia;

  beforeEach((): void => {
    pinia = createPinia();
    setActivePinia(pinia);
    localStorage.clear();
  });

  afterEach((): void => {
    wrapper?.unmount();
  });

  function createWrapper(props: { drawer?: boolean } = {}): VueWrapper<InstanceType<typeof SponsorshipView>> {
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
      version: '1.43.0',
    });

    wrapper = createWrapper();

    expect(wrapper.text()).toContain('1.43.0');
  });

  it('should display the new sponsor name', () => {
    wrapper = createWrapper();
    expect(wrapper.text()).toContain(SPONSOR_NAME);
  });

  it('should display the sponsor image on login screen', () => {
    wrapper = createWrapper({ drawer: false });

    const appImage = wrapper.findComponent({ name: 'AppImage' });
    expect(appImage.attributes('src')).toBe(SPONSOR_IMAGE);
  });

  it('should display the same sponsor image on drawer', () => {
    wrapper = createWrapper({ drawer: true });

    const appImage = wrapper.findComponent({ name: 'AppImage' });
    expect(appImage.attributes('src')).toBe(SPONSOR_IMAGE);
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

  it('should not modify sponsorship login index in local storage', () => {
    localStorage.setItem('rotki.sponsorship.login_index', '1');

    wrapper = createWrapper({ drawer: false });

    expect(localStorage.getItem('rotki.sponsorship.login_index')).toBe('1');
  });
});
