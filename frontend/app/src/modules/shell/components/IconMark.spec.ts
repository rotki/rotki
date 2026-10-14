import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getPublicPlaceholderImagePath } from '@/modules/core/common/file/file';
import { fillsFrame } from '@/modules/shell/components/icon-mark-shape';
import IconMark from '@/modules/shell/components/IconMark.vue';

vi.mock('@/modules/shell/components/icon-mark-shape', () => ({
  fillsFrame: vi.fn((): boolean => false),
}));

const stubs = {
  RuiSkeletonLoader: { template: '<div data-testid="skeleton" />' },
};

function createWrapper(props: { src?: string; size?: string | number; backing?: 'light' | 'dark'; loading?: boolean } = {}): VueWrapper<InstanceType<typeof IconMark>> {
  return mount(IconMark, {
    global: { stubs },
    props: { alt: 'Logo', size: '24px', src: 'https://example.com/logo.png', ...props },
  });
}

function frame(wrapper: VueWrapper): HTMLElement {
  const element = wrapper.find('[data-testid=icon-mark]').element;
  if (!(element instanceof HTMLElement))
    throw new Error('no frame');
  return element;
}

describe('modules/shell/components/IconMark', () => {
  beforeEach(() => {
    vi.mocked(fillsFrame).mockReset();
    vi.mocked(fillsFrame).mockReturnValue(false);
  });

  it('should show a skeleton instead of the image while loading', () => {
    const wrapper = createWrapper({ loading: true });

    expect(wrapper.find('[data-testid=skeleton]').exists()).toBe(true);
    expect(wrapper.find('img').exists()).toBe(false);
  });

  it('should render nothing inside the frame without a source', () => {
    const wrapper = createWrapper({ src: undefined });

    expect(wrapper.find('img').exists()).toBe(false);
  });

  it('should ask for a CORS response first, so the edges can be read', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('img').attributes('crossorigin')).toBe('anonymous');
  });

  it('should crop a logo that fills the frame, without a backing', async () => {
    vi.mocked(fillsFrame).mockReturnValue(true);
    const wrapper = createWrapper();
    await wrapper.find('img').trigger('load');

    expect(fillsFrame).toHaveBeenCalledOnce();
    expect(wrapper.emitted('load')).toEqual([[]]);
    expect(wrapper.find('img').classes()).toContain('object-cover');
    expect(wrapper.find('[data-testid=icon-mark]').classes()).not.toContain('dark:bg-white');
  });

  it('should give a glyph a light backing and keep it contained', async () => {
    const wrapper = createWrapper();
    await wrapper.find('img').trigger('load');

    expect(fillsFrame).toHaveBeenCalledOnce();
    expect(wrapper.find('img').classes()).toContain('object-contain');
    expect(wrapper.find('[data-testid=icon-mark]').classes()).toContain('dark:bg-white');
  });

  it('should give a logo drawn for dark pages a dark backing', () => {
    const wrapper = createWrapper({ backing: 'dark' });

    expect(wrapper.find('[data-testid=icon-mark]').classes()).toContain('dark:bg-black');
  });

  it('should size the frame from the size prop', () => {
    const wrapper = createWrapper({ size: '2rem' });

    expect(frame(wrapper).style.width).toBe('2rem');
    expect(frame(wrapper).style.height).toBe('2rem');
  });

  it('should retry without CORS on a first error, then never read the edges', async () => {
    const wrapper = createWrapper();
    await wrapper.find('img').trigger('error');

    expect(wrapper.emitted('error')).toBeUndefined();
    expect(wrapper.find('img').attributes('crossorigin')).toBeUndefined();
    expect(wrapper.find('img').attributes('src')).toBe('https://example.com/logo.png');

    await wrapper.find('img').trigger('load');

    expect(fillsFrame).not.toHaveBeenCalled();
    expect(wrapper.emitted('load')).toEqual([[]]);
  });

  it('should fall back to the placeholder and report the error when the plain load fails too', async () => {
    const wrapper = createWrapper();
    await wrapper.find('img').trigger('error');
    await wrapper.find('img').trigger('error');

    expect(wrapper.emitted('error')).toEqual([[]]);
    expect(wrapper.find('img').attributes('src')).toBe(getPublicPlaceholderImagePath('image.svg'));
  });

  it('should start over with CORS and the real image when the source changes', async () => {
    vi.mocked(fillsFrame).mockReturnValue(true);
    const wrapper = createWrapper();
    await wrapper.find('img').trigger('load');
    expect(wrapper.find('img').classes()).toContain('object-cover');

    await wrapper.setProps({ src: 'https://example.com/other.png' });

    expect(wrapper.find('img').classes()).toContain('object-contain');
    expect(wrapper.find('img').attributes('crossorigin')).toBe('anonymous');

    await wrapper.find('img').trigger('error');
    await wrapper.find('img').trigger('error');
    await wrapper.setProps({ src: 'https://example.com/third.png' });

    expect(wrapper.find('img').attributes('src')).toBe('https://example.com/third.png');
    expect(wrapper.find('img').attributes('crossorigin')).toBe('anonymous');
  });

  it('should pass loadstart through', async () => {
    const wrapper = createWrapper();
    await wrapper.find('img').trigger('loadstart');

    expect(wrapper.emitted('loadstart')).toEqual([[]]);
  });
});
