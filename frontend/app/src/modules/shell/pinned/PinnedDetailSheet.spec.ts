import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import PinnedDetailSheet from '@/modules/shell/pinned/PinnedDetailSheet.vue';
import { createRuiPlugin } from '@/plugins/rui';

function createWrapper(open: boolean, slots: Record<string, string> = {}): VueWrapper<InstanceType<typeof PinnedDetailSheet>> {
  return mount(PinnedDetailSheet, {
    global: {
      plugins: [createRuiPlugin({})],
    },
    props: { modelValue: open },
    slots: {
      default: '<div data-testid="sheet-body">body</div>',
      ...slots,
    },
  });
}

describe('pinnedDetailSheet', () => {
  it('should render neither the sheet nor the scrim while closed', () => {
    const wrapper = createWrapper(false);

    expect(wrapper.find('[data-testid=pinned-detail-sheet]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=pinned-detail-sheet-scrim]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=sheet-body]').exists()).toBe(false);
  });

  it('should render the body and the scrim while open', () => {
    const wrapper = createWrapper(true);

    expect(wrapper.find('[data-testid=pinned-detail-sheet]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=pinned-detail-sheet-scrim]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=sheet-body]').text()).toBe('body');
  });

  it('should close when the scrim is clicked', async () => {
    const wrapper = createWrapper(true);

    await wrapper.find('[data-testid=pinned-detail-sheet-scrim]').trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
  });

  it('should render the header slot when one is provided', () => {
    const wrapper = createWrapper(true, { header: '<div data-testid="sheet-header">title</div>' });

    expect(wrapper.find('[data-testid=sheet-header]').text()).toBe('title');
  });

  it('should position itself absolutely so it stays inside the pinned panel', () => {
    // The rail keeps backgrounded panels alive, so a teleported overlay would leak out of its
    // panel. Absolute placement is what keeps the sheet scoped to its host.
    const wrapper = createWrapper(true);

    const classes = wrapper.find('[data-testid=pinned-detail-sheet]').classes();
    expect(classes).toContain('absolute');
    expect(classes).toContain('bottom-0');
  });

  it('should apply the default height and allow overriding it', () => {
    const defaultSheet = createWrapper(true);
    expect(defaultSheet.find('[data-testid=pinned-detail-sheet]').attributes('style')).toContain('height: 95%');

    const shortSheet = mount(PinnedDetailSheet, {
      global: { plugins: [createRuiPlugin({})] },
      props: { height: '60%', modelValue: true },
      slots: { default: '<div />' },
    });
    expect(shortSheet.find('[data-testid=pinned-detail-sheet]').attributes('style')).toContain('height: 60%');
  });
});
