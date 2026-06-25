import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';

describe('scrollable-dialog-content', () => {
  function createWrapper(options: ComponentMountingOptions<typeof ScrollableDialogContent> = {}): VueWrapper {
    return mount(ScrollableDialogContent, {
      ...options,
      slots: {
        default: '<div data-testid="body">body</div>',
        ...options.slots,
      },
    });
  }

  function bodyRegion(wrapper: VueWrapper): Element {
    const body = wrapper.find('[data-testid=body]').element.parentElement;
    if (!body)
      throw new Error('body region not found');
    return body;
  }

  it('should make the body region the scroll container', () => {
    // The whole point of the component: the scrollable region must carry
    // `flex-1 min-h-0 overflow-y-auto`. `min-h-0` is load-bearing — without it a
    // flex child will not shrink below its content and never scrolls. Guard it.
    const region = bodyRegion(createWrapper());
    expect(region.className).toContain('flex-1');
    expect(region.className).toContain('min-h-0');
    expect(region.className).toContain('overflow-y-auto');
  });

  it('should bound the column so the body can absorb leftover space', () => {
    const root = createWrapper().element;
    expect(root.className).toContain('flex');
    expect(root.className).toContain('flex-col');
    expect(root.className).toContain('max-h-[90vh]');
  });

  it('should grow within a flex-column parent when `fill` is set', () => {
    const root = createWrapper({ props: { fill: true } }).element;
    expect(root.className).toContain('flex-1');
    expect(root.className).toContain('min-h-0');
    expect(root.className).not.toContain('max-h-[90vh]');
  });

  it('should apply an explicit cap when `maxHeight` is set', () => {
    const root = createWrapper({ props: { maxHeight: 'calc(100vh - 10rem)' } }).element;
    expect(root.className).not.toContain('max-h-[90vh]');
    expect(root.getAttribute('style')).toContain('max-height: calc(100vh - 10rem)');
  });

  it('should prefer `fill` over `maxHeight`', () => {
    const root = createWrapper({ props: { fill: true, maxHeight: 'calc(100vh - 10rem)' } }).element;
    expect(root.className).toContain('flex-1');
    expect(root.getAttribute('style') ?? '').not.toContain('max-height');
  });

  it('should pin the header above the scroll area', () => {
    const wrapper = createWrapper({
      slots: {
        header: '<div data-testid="header">header</div>',
        default: '<div data-testid="body">body</div>',
      },
    });
    const header = wrapper.find('[data-testid=header]').element.parentElement;
    expect(header?.className).toContain('shrink-0');
  });

  it('should pin the footer below the scroll area', () => {
    const wrapper = createWrapper({
      slots: {
        default: '<div data-testid="body">body</div>',
        footer: '<div data-testid="footer">footer</div>',
      },
    });
    const footer = wrapper.find('[data-testid=footer]').element.parentElement;
    expect(footer?.className).toContain('shrink-0');
  });

  it('should not render header/footer wrappers when those slots are absent', () => {
    const wrapper = createWrapper();
    // only the body wrapper should exist as a direct child
    expect(wrapper.element.children).toHaveLength(1);
  });
});
