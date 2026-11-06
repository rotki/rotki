import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import HistoryEventsSwapCollapseRow from '@/modules/history/events/components/HistoryEventsSwapCollapseRow.vue';

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = {
  name: 'RuiMenu',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
};

const unlinkConfirm = { confirmLabel: 'Unlink', message: 'Unlink this bridge transfer?', title: 'Unlink' };

/**
 * Seam: the header of an expanded subgroup offers unlink only when the parent hands it the question
 * to ask, whether it is a matched bridge or a matched movement, and never for a plain swap. The
 * header asks beside the button and emits only once accepted.
 */
describe('modules/history/events/components/HistoryEventsSwapCollapseRow', () => {
  let wrapper: VueWrapper | undefined;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  function mountRow(props: { canUnlink?: boolean; labelType?: 'swap' | 'movement' | 'bridge' }): VueWrapper {
    const { canUnlink, ...rest } = props;
    wrapper = mount(HistoryEventsSwapCollapseRow, {
      global: { provide: libraryDefaults, stubs: { RuiMenu } },
      props: { eventCount: 2, unlinkConfirm: canUnlink ? unlinkConfirm : undefined, ...rest },
    });
    return wrapper;
  }

  it('should ask beside the unlink button before emitting', async () => {
    const row = mountRow({ canUnlink: true, labelType: 'bridge' });

    await row.find('[data-testid="collapse-unlink"]').trigger('click');

    expect(row.find('[data-testid="inline-confirm"]').text()).toContain('Unlink this bridge transfer?');
    expect(row.emitted('unlink-event')).toBeUndefined();
  });

  it('should emit unlink from a matched bridge header once accepted', async () => {
    const row = mountRow({ canUnlink: true, labelType: 'bridge' });

    await row.find('[data-testid="collapse-unlink"]').trigger('click');
    await row.find('[data-testid="inline-confirm-accept"]').trigger('click');

    expect(row.emitted('unlink-event')).toHaveLength(1);
  });

  it('should keep the unlink click from collapsing the header', async () => {
    const row = mountRow({ canUnlink: true, labelType: 'bridge' });

    await row.find('[data-testid="collapse-unlink"]').trigger('click');

    expect(row.emitted('collapse')).toBeUndefined();
  });

  it('should not emit when the question is cancelled', async () => {
    const row = mountRow({ canUnlink: true, labelType: 'movement' });

    await row.find('[data-testid="collapse-unlink"]').trigger('click');
    await row.find('[data-testid="inline-confirm-cancel"]').trigger('click');

    expect(row.emitted('unlink-event')).toBeUndefined();
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

  // A read-only view (the accounting rule preview) withholds the question, and unlink really unlinks.
  it('should not offer unlink on a movement header when the parent withholds it', () => {
    const row = mountRow({ labelType: 'movement' });

    expect(row.find('[data-testid="collapse-unlink"]').exists()).toBe(false);
  });
});
