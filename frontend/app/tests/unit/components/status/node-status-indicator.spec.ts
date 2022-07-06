import { mount, Wrapper } from '@vue/test-utils';
import NodeStatusIndicator from '@/components/status/NodeStatusIndicator.vue';
import store from '@/store/store';
import { mountOptions } from '../../utils/mount';

describe('NodeStatusIndicator.vue', () => {
  let wrapper: Wrapper<any>;

  beforeEach(() => {
    document.body.setAttribute('data-app', 'true');
    const options = mountOptions();
    wrapper = mount(NodeStatusIndicator, {
      ...options
    });
  });

  afterEach(() => {
    store.commit('session/reset');
  });

  test('shows connected when node connections is true', async () => {
    expect.assertions(4);
    store.commit('session/nodeConnection', true);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.mdi-link').exists()).toBe(true);

    wrapper.find('[data-cy=status-indicator] button').trigger('click');
    await wrapper.vm.$nextTick();

    const icon = wrapper.find('[data-cy="status-icon"]');
    expect(icon.exists()).toBe(true);
    expect(icon.classes()).toContain('mdi-check-circle');
    expect(wrapper.find('[data-cy="status-text"]').text()).toContain(
      'connected'
    );
  });

  test('shows disconnected when node connection is false', async () => {
    expect.assertions(4);
    store.commit('session/nodeConnection', false);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.mdi-link-off').exists()).toBe(true);

    wrapper.find('[data-cy=status-indicator] button').trigger('click');
    await wrapper.vm.$nextTick();

    const icon = wrapper.find('[data-cy="status-icon"]');
    expect(icon.exists()).toBe(true);
    expect(icon.classes()).toContain('mdi-alert');
    expect(wrapper.find('[data-cy="status-text"]').text()).toContain(
      'disconnected'
    );
  });
});
