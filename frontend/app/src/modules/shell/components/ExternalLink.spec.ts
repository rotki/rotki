import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

vi.mock('@/modules/shell/app/use-electron-interop', (): Record<string, unknown> => ({
  useInterop: (): { isPackaged: boolean; openUrl: ReturnType<typeof vi.fn> } => ({
    isPackaged: false,
    openUrl: vi.fn(),
  }),
}));

vi.mock('@shared/external-links', (): Record<string, unknown> => ({
  externalLinks: {
    premium: 'https://rotki.com/products',
  },
}));

describe('external-link', () => {
  let wrapper: VueWrapper<InstanceType<typeof ExternalLink>>;

  afterEach((): void => {
    wrapper?.unmount();
  });

  it('should render an anchor when url is provided', () => {
    wrapper = mount(ExternalLink, {
      props: { url: 'https://example.com' },
      slots: { default: 'click me' },
    });

    const anchor = wrapper.find('a');
    expect(anchor.exists()).toBe(true);
    expect(anchor.attributes('href')).toBe('https://example.com');
    expect(anchor.attributes('target')).toBe('_blank');
    expect(anchor.text()).toBe('click me');
  });

  it('should render the text prop when no default slot is provided', () => {
    wrapper = mount(ExternalLink, {
      props: { text: 'fallback', url: 'https://example.com' },
    });

    expect(wrapper.find('a').text()).toBe('fallback');
  });

  it('should apply the primary color class by default', () => {
    wrapper = mount(ExternalLink, { props: { url: 'https://example.com' } });

    const classes = wrapper.find('a').classes();
    expect(classes).toContain('text-rui-primary');
    expect(classes).toContain('underline');
  });

  it('should apply the warning color class when color="warning"', () => {
    wrapper = mount(ExternalLink, {
      props: { color: 'warning', url: 'https://example.com' },
    });

    expect(wrapper.find('a').classes()).toContain('text-rui-warning');
  });

  it('should render an anchor wrapping the slot when custom is true', () => {
    wrapper = mount(ExternalLink, {
      props: { custom: true, url: 'https://example.com' },
      slots: { default: '<button data-test="inner">go</button>' },
    });

    const anchor = wrapper.find('a');
    expect(anchor.exists()).toBe(true);
    expect(anchor.attributes('href')).toBe('https://example.com');
    expect(anchor.find('[data-test="inner"]').exists()).toBe(true);
    expect(anchor.classes()).not.toContain('underline');
  });

  it('should use the premium url when premium is true and no url provided', () => {
    wrapper = mount(ExternalLink, { props: { premium: true } });

    expect(wrapper.find('a').attributes('href')).toBe('https://rotki.com/products');
  });

  it('should render a div with the slot when neither url nor premium is set', () => {
    wrapper = mount(ExternalLink, {
      slots: { default: 'plain' },
    });

    expect(wrapper.find('a').exists()).toBe(false);
    expect(wrapper.find('div').exists()).toBe(true);
    expect(wrapper.text()).toBe('plain');
  });

  it('should show the confirmation dialog on click when confirm is true', async () => {
    wrapper = mount(ExternalLink, {
      attachTo: document.body,
      props: { confirm: true, url: 'https://example.com' },
      slots: { default: 'click' },
    });

    await wrapper.find('a').trigger('click');
    await nextTick();

    expect(document.body.textContent).toContain('https://example.com');
  });
});
