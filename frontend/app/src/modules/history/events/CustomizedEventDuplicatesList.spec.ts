import type { DuplicateRow } from '@/modules/history/events/use-customized-event-duplicates';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import CustomizedEventDuplicatesList from '@/modules/history/events/CustomizedEventDuplicatesList.vue';
import '@test/i18n';

const RuiDataTable = defineComponent({
  name: 'RuiDataTable',
  props: ['empty'],
  template: '<div><slot name="body.prepend" /><div data-testid="empty"><slot name="empty-description" /></div></div>',
});

function mountList(state: { error?: unknown; rows?: DuplicateRow[] } = {}): VueWrapper {
  return mount(CustomizedEventDuplicatesList, {
    global: { provide: libraryDefaults, stubs: { RuiDataTable } },
    props: { description: 'description', error: state.error, rows: state.rows ?? [] },
  });
}

describe('customizedEventDuplicatesList', () => {
  it('should name a failed read with no rows in the empty state, with a retry', async () => {
    const wrapper = mountList({ error: new Error('backend down') });

    expect(wrapper.findComponent(RuiDataTable).props('empty')).toEqual({ label: 'customized_event_duplicates.load_failed' });
    expect(wrapper.find('[data-testid=table-failure-message]').text()).toBe('backend down');
    await wrapper.find('[data-testid=table-failure-retry]').trigger('click');

    expect(wrapper.emitted('retry')).toHaveLength(1);
  });

  it('should name a failed read in a strip above the rows an earlier read left, with a retry', async () => {
    const wrapper = mountList({ error: new Error('backend down'), rows: [createMock<DuplicateRow>()] });

    expect(wrapper.find('[data-testid=duplicates-load-error]').text()).toContain('backend down');
    await wrapper.find('[data-testid=table-failure-strip-retry]').trigger('click');

    expect(wrapper.emitted('retry')).toHaveLength(1);
  });

  it('should say there are no duplicates while nothing failed', () => {
    const wrapper = mountList();

    expect(wrapper.findComponent(RuiDataTable).props('empty')).toEqual({ description: 'customized_event_duplicates.no_items' });
    expect(wrapper.find('[data-testid=duplicates-load-error]').exists()).toBe(false);
  });
});
