import type { SnapshotChange } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import SnapshotEditorToolbar from '@/modules/dashboard/snapshots/components/SnapshotEditorToolbar.vue';

const TIMESTAMP = 1_600_000_000;

const CHANGE: SnapshotChange = { after: bigNumberify(120), before: bigNumberify(100), kind: 'total-changed' };

function mountToolbar(props: Record<string, unknown> = {}): VueWrapper {
  return mount(SnapshotEditorToolbar, {
    global: {
      provide: libraryDefaults,
      stubs: {
        DateDisplay: true,
        SnapshotChangesList: true,
      },
    },
    props: { changes: [], timestamp: TIMESTAMP, ...props },
  });
}

describe('snapshotEditorToolbar', () => {
  it('should disable navigation at the ends of the range', () => {
    const wrapper = mountToolbar({ hasNext: false, hasPrev: false });
    expect(wrapper.find('[data-testid=snapshot-nav-prev]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=snapshot-nav-next]').attributes('disabled')).toBeDefined();
  });

  it('should emit navigate in both directions', async () => {
    const wrapper = mountToolbar({ hasNext: true, hasPrev: true });
    await wrapper.find('[data-testid=snapshot-nav-prev]').trigger('click');
    await wrapper.find('[data-testid=snapshot-nav-next]').trigger('click');
    expect(wrapper.emitted('navigate')).toEqual([['prev'], ['next']]);
  });

  it('should disable save, discard and undo when there is nothing to do', () => {
    const wrapper = mountToolbar({ canUndo: false, changes: [] });
    expect(wrapper.find('[data-testid=snapshot-save]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=snapshot-discard]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=snapshot-undo]').attributes('disabled')).toBeDefined();
  });

  it('should emit save, discard and undo when enabled', async () => {
    const wrapper = mountToolbar({ canUndo: true, changes: [CHANGE] });
    await wrapper.find('[data-testid=snapshot-save]').trigger('click');
    await wrapper.find('[data-testid=snapshot-discard]').trigger('click');
    await wrapper.find('[data-testid=snapshot-undo]').trigger('click');
    expect(wrapper.emitted('save')).toHaveLength(1);
    expect(wrapper.emitted('discard')).toHaveLength(1);
    expect(wrapper.emitted('undo')).toHaveLength(1);
  });

  it('should show the dirty badge only when there are changes', () => {
    expect(mountToolbar({ changes: [] }).find('[data-testid=snapshot-dirty-badge]').exists()).toBe(false);
    expect(mountToolbar({ changes: [CHANGE] }).find('[data-testid=snapshot-dirty-badge]').exists()).toBe(true);
  });
});
