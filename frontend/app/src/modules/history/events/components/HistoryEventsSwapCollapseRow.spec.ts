import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import HistoryEventsSwapCollapseRow from '@/modules/history/events/components/HistoryEventsSwapCollapseRow.vue';

/**
 * Seam: the header of an expanded subgroup offers unlink only when the parent says the subgroup
 * can be unlinked, whether it is a matched bridge or a matched movement, and never for a plain swap.
 */
describe('modules/history/events/components/HistoryEventsSwapCollapseRow', () => {
  let wrapper: VueWrapper | undefined;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  function mountRow(props: { canUnlink?: boolean; labelType?: 'swap' | 'movement' | 'bridge' }): VueWrapper {
    wrapper = mount(HistoryEventsSwapCollapseRow, {
      global: { provide: libraryDefaults },
      props: { eventCount: 2, ...props },
    });
    return wrapper;
  }

  it('should emit unlink from a matched bridge header', async () => {
    const row = mountRow({ canUnlink: true, labelType: 'bridge' });

    await row.find('[data-testid="collapse-unlink"]').trigger('click');
    expect(row.emitted('unlink-event')).toHaveLength(1);
  });

  it('should not offer unlink on a bridge header that cannot be unlinked', () => {
    const row = mountRow({ labelType: 'bridge' });

    expect(row.find('[data-testid="collapse-unlink"]').exists()).toBe(false);
  });

  it('should not offer unlink on a swap header', () => {
    const row = mountRow({ labelType: 'swap' });

    expect(row.find('[data-testid="collapse-unlink"]').exists()).toBe(false);
  });

  it('should offer unlink on a matched movement header', () => {
    const row = mountRow({ canUnlink: true, labelType: 'movement' });

    expect(row.find('[data-testid="collapse-unlink"]').exists()).toBe(true);
  });

  // A read-only view (the accounting rule preview) withholds canUnlink, and unlink really unlinks.
  it('should not offer unlink on a movement header when the parent withholds it', () => {
    const row = mountRow({ labelType: 'movement' });

    expect(row.find('[data-testid="collapse-unlink"]').exists()).toBe(false);
  });
});
