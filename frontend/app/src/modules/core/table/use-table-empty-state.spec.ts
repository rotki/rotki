import { mount } from '@vue/test-utils';
import { FetchError } from 'ofetch';
import { describe, expect, it } from 'vitest';
import { type Component, defineComponent, h } from 'vue';
import { toRequestError } from '@/modules/core/api/request-result';
import { createStatusError } from '@/modules/core/api/response-handlers';
import { provideTableFetchError, useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import '@test/i18n';

/** Renders the resolved empty state as text, so a mounted tree can be asserted on. */
function leaf(options: Parameters<typeof useTableEmptyState>[0] = {}): Component {
  return defineComponent({
    setup() {
      const emptyState = useTableEmptyState(options);
      return (): ReturnType<typeof h> => h('div', `${get(emptyState).label ?? ''}|${get(emptyState).description ?? ''}`);
    },
  });
}

function parentProviding(error: Ref<unknown>, child: Component): Component {
  return defineComponent({
    setup() {
      provideTableFetchError(error);
      return (): ReturnType<typeof h> => h(child);
    },
  });
}

describe('useTableEmptyState', () => {
  it('should fall back to the generic no-data text when nothing failed', () => {
    const wrapper = mount(leaf());

    expect(wrapper.text()).toBe('|data_table.no_data');
  });

  it('should prefer the caller\'s own empty text over the generic one', () => {
    const wrapper = mount(leaf({ fallback: { description: 'nothing here yet' } }));

    expect(wrapper.text()).toBe('|nothing here yet');
  });

  it('should name the failure instead of the empty text once a fetch fails', () => {
    const wrapper = mount(leaf({ error: ref<unknown>(new Error('backend is down')) }));

    expect(wrapper.text()).toBe('data_table.fetch_failed|backend is down');
  });

  it('should name an unreachable backend in words instead of the raw request line', () => {
    const unreachable = toRequestError(new FetchError('[GET] "http://127.0.0.1:13024/api/1/nfts/balances": <no response> fetch failed'));
    const wrapper = mount(leaf({ error: ref<unknown>(unreachable) }));

    expect(wrapper.text()).toBe('data_table.fetch_failed|common.backend_unreachable');
  });

  it('should keep the backend\'s own message for a request it answered', () => {
    const refused = createStatusError(500, 'Report 3 does not exist', { message: 'Report 3 does not exist' });
    const wrapper = mount(leaf({ error: ref<unknown>(toRequestError(refused)) }));

    expect(wrapper.text()).toBe('data_table.fetch_failed|Report 3 does not exist');
  });

  it('should go back to the empty text once a later fetch succeeds', async () => {
    const error = ref<unknown>(new Error('backend is down'));
    const wrapper = mount(leaf({ error }));

    set(error, undefined);
    await nextTick();

    expect(wrapper.text()).toBe('|data_table.no_data');
  });

  it('should read the failure a server table provided further up the tree', () => {
    const error = ref<unknown>(new Error('provided failure'));
    const wrapper = mount(parentProviding(error, leaf()));

    expect(wrapper.text()).toBe('data_table.fetch_failed|provided failure');
  });

  it('should prefer an explicitly passed failure over the provided one', () => {
    const wrapper = mount(parentProviding(
      ref<unknown>(new Error('provided failure')),
      leaf({ error: ref<unknown>(new Error('own failure')) }),
    ));

    expect(wrapper.text()).toBe('data_table.fetch_failed|own failure');
  });
});
