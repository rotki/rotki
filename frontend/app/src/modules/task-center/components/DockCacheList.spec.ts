import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import DockCacheList from '@/modules/task-center/components/DockCacheList.vue';

const CURVE = { chain: 'ethereum', processed: 18, protocol: 'curve', total: 44 };
const AAVE = { chain: 'ethereum', processed: 44, protocol: 'aave', total: 44 };
const YEARN = { chain: 'optimism', processed: 9, protocol: 'yearn', total: 9 };

function createWrapper(props: InstanceType<typeof DockCacheList>['$props']): VueWrapper {
  return mount(DockCacheList, {
    props,
    global: {
      stubs: { ChainIcon: true, CounterpartyDisplay: { props: ['counterparty'], template: '<span>{{ counterparty }}</span>' } },
    },
  });
}

function rows(wrapper: VueWrapper): string[] {
  return wrapper.findAll('[data-testid=dock-cache-row]').map(row => row.text());
}

describe('dockCacheList', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should list every filling cache with its protocol and count, and hide the filled ones behind a toggle', () => {
    const wrapper = createWrapper({ filled: [AAVE, YEARN], filling: [CURVE], stopped: [] });

    expect(rows(wrapper)).toHaveLength(1);
    expect(rows(wrapper)[0]).toContain('curve');
    expect(rows(wrapper)[0]).toContain('pending_task.steps::18, 44');
    expect(wrapper.find('[data-testid=dock-cache-filled-toggle]').text()).toContain('task_dock.detail.caches_filled::2');
  });

  it('should show the filled caches on toggle and hide them again', async () => {
    const wrapper = createWrapper({ filled: [AAVE, YEARN], filling: [CURVE], stopped: [] });
    const toggle = wrapper.find('[data-testid=dock-cache-filled-toggle]');

    await toggle.trigger('click');
    expect(rows(wrapper)).toHaveLength(3);
    expect(toggle.attributes('aria-expanded')).toBe('true');

    await toggle.trigger('click');
    expect(rows(wrapper)).toHaveLength(1);
  });

  it('should draw a bar only on a cache still filling', () => {
    const wrapper = createWrapper({ filled: [], filling: [CURVE], stopped: [] });

    expect(wrapper.find('[data-testid=dock-cache-row] [style]').attributes('style')).toContain('width: 41%');
  });

  it('should offer no toggle when nothing is filled yet', () => {
    expect(createWrapper({ filled: [], filling: [CURVE], stopped: [] }).find('[data-testid=dock-cache-filled-toggle]').exists()).toBe(false);
  });

  it('should list a stopped cache openly, marked stopped and with no bar', () => {
    const row = createWrapper({ filled: [AAVE], filling: [], stopped: [CURVE] }).find('[data-testid=dock-cache-row]');

    expect(row.find('[data-testid=dock-cache-stopped]').exists()).toBe(true);
    expect(row.find('[style]').exists()).toBe(false);
    expect(row.text()).toContain('pending_task.steps::18, 44');
  });
});
