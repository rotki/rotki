import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import HistoryRefreshButton from '@/modules/history/refresh/HistoryRefreshButton.vue';

describe('historyRefreshButton', () => {
  it('should ask for a full refresh straight away when refresh is clicked', async () => {
    const wrapper = mount(HistoryRefreshButton, {
      global: { stubs: { HistoryRefreshSelection: true } },
      props: { processing: false },
    });

    await wrapper.find('[data-testid=history-refresh-all]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[]]);
  });
});
