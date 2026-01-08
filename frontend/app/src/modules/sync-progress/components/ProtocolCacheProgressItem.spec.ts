import type { ProtocolCacheProgress } from '../types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { setupSyncProgressMocks } from '../test-utils';
import ProtocolCacheProgressItem from './ProtocolCacheProgressItem.vue';

setupSyncProgressMocks();

describe('modules/sync-progress/components/ProtocolCacheProgressItem', () => {
  let wrapper: VueWrapper<InstanceType<typeof ProtocolCacheProgressItem>>;
  let pinia: Pinia;

  function createProtocolCacheProgress(
    processed: number,
    total: number,
    chain = 'eth',
    protocol = 'uniswap_v3',
  ): ProtocolCacheProgress {
    return {
      chain,
      processed,
      progress: total > 0 ? Math.round((processed / total) * 100) : 0,
      protocol,
      total,
    };
  }

  function createWrapper(item: ProtocolCacheProgress, compact = false): VueWrapper<InstanceType<typeof ProtocolCacheProgressItem>> {
    return mount(ProtocolCacheProgressItem, {
      global: {
        plugins: [pinia],
        stubs: {
          ChainIcon: {
            template: '<span data-testid="chain-icon">{{ chain }}</span>',
            props: ['chain', 'size'],
          },
          CounterpartyDisplay: {
            template: '<span data-testid="counterparty-display">{{ counterparty }}</span>',
            props: ['counterparty', 'size'],
          },
          RuiIcon: {
            template: '<span data-testid="icon" :class="[$attrs.class]">{{ name }}</span>',
            props: ['name', 'size'],
          },
          RuiProgress: {
            template: '<div data-testid="progress" :data-value="value" :data-color="color"></div>',
            props: ['value', 'color', 'size', 'rounded'],
          },
        },
      },
      props: {
        compact,
        item,
      },
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('status display', () => {
    it('should display complete status when processed >= total', () => {
      const item = createProtocolCacheProgress(100, 100);
      wrapper = createWrapper(item);

      expect(wrapper.text()).toContain('sync_progress.status.complete');
      expect(wrapper.find('[data-testid="icon"]').text()).toBe('lu-check');
    });

    it('should display pending status when processed is 0', () => {
      const item = createProtocolCacheProgress(0, 100);
      wrapper = createWrapper(item);

      expect(wrapper.text()).toContain('sync_progress.status.pending');
      expect(wrapper.find('[data-testid="icon"]').text()).toBe('lu-circle');
    });

    it('should display refreshing status when in progress', () => {
      const item = createProtocolCacheProgress(50, 100);
      wrapper = createWrapper(item);

      expect(wrapper.text()).toContain('sync_progress.status.refreshing');
      expect(wrapper.find('[data-testid="icon"]').text()).toBe('lu-loader-circle');
    });
  });

  describe('icon styling', () => {
    it('should apply success color for complete status', () => {
      const item = createProtocolCacheProgress(100, 100);
      wrapper = createWrapper(item);

      const icon = wrapper.find('[data-testid="icon"]');
      expect(icon.classes()).toContain('text-rui-success');
    });

    it('should apply primary color and animation for in-progress status', () => {
      const item = createProtocolCacheProgress(50, 100);
      wrapper = createWrapper(item);

      const icon = wrapper.find('[data-testid="icon"]');
      expect(icon.classes()).toContain('text-rui-primary');
      expect(icon.classes()).toContain('animate-spin');
    });

    it('should apply disabled color for pending status', () => {
      const item = createProtocolCacheProgress(0, 100);
      wrapper = createWrapper(item);

      const icon = wrapper.find('[data-testid="icon"]');
      expect(icon.classes()).toContain('text-rui-text-disabled');
    });
  });

  describe('progress bar', () => {
    it('should show progress bar in normal mode', () => {
      const item = createProtocolCacheProgress(50, 100);
      wrapper = createWrapper(item);

      const progress = wrapper.find('[data-testid="progress"]');
      expect(progress.exists()).toBe(true);
      expect(progress.attributes('data-value')).toBe('50');
    });

    it('should hide progress bar in compact mode', () => {
      const item = createProtocolCacheProgress(50, 100);
      wrapper = createWrapper(item, true);

      expect(wrapper.find('[data-testid="progress"]').exists()).toBe(false);
    });

    it('should apply correct color based on status', () => {
      const completedItem = createProtocolCacheProgress(100, 100);
      wrapper = createWrapper(completedItem);
      expect(wrapper.find('[data-testid="progress"]').attributes('data-color')).toBe('success');
      wrapper.unmount();

      const inProgressItem = createProtocolCacheProgress(50, 100);
      wrapper = createWrapper(inProgressItem);
      expect(wrapper.find('[data-testid="progress"]').attributes('data-color')).toBe('primary');
      wrapper.unmount();

      const pendingItem = createProtocolCacheProgress(0, 100);
      wrapper = createWrapper(pendingItem);
      expect(wrapper.find('[data-testid="progress"]').attributes('data-color')).toBe('secondary');
    });
  });

  describe('chain and protocol display', () => {
    it('should display chain icon', () => {
      const item = createProtocolCacheProgress(50, 100, 'optimism');
      wrapper = createWrapper(item);

      const chainIcon = wrapper.find('[data-testid="chain-icon"]');
      expect(chainIcon.exists()).toBe(true);
      expect(chainIcon.text()).toBe('optimism');
    });

    it('should display counterparty', () => {
      const item = createProtocolCacheProgress(50, 100, 'eth', 'uniswap_v3');
      wrapper = createWrapper(item);

      const counterpartyDisplay = wrapper.find('[data-testid="counterparty-display"]');
      expect(counterpartyDisplay.exists()).toBe(true);
      expect(counterpartyDisplay.text()).toBe('uniswap_v3');
    });

    it('should display progress counts', () => {
      const item = createProtocolCacheProgress(50, 100);
      wrapper = createWrapper(item);

      expect(wrapper.text()).toContain('sync_progress.protocol_cache_progress');
    });
  });

  describe('visual feedback', () => {
    it('should animate for in-progress protocol cache', () => {
      const item = createProtocolCacheProgress(50, 100);
      wrapper = createWrapper(item);

      expect(wrapper.classes()).toContain('animate-pulse');
    });

    it('should not animate for complete protocol cache', () => {
      const item = createProtocolCacheProgress(100, 100);
      wrapper = createWrapper(item);

      expect(wrapper.classes()).not.toContain('animate-pulse');
    });

    it('should not animate for pending protocol cache', () => {
      const item = createProtocolCacheProgress(0, 100);
      wrapper = createWrapper(item);

      expect(wrapper.classes()).not.toContain('animate-pulse');
    });
  });

  describe('border styling', () => {
    it('should apply success border for complete status', () => {
      const item = createProtocolCacheProgress(100, 100);
      wrapper = createWrapper(item);

      expect(wrapper.classes()).toContain('border-l-rui-success');
    });

    it('should apply primary border for in-progress status', () => {
      const item = createProtocolCacheProgress(50, 100);
      wrapper = createWrapper(item);

      expect(wrapper.classes()).toContain('border-l-rui-primary');
    });
  });
});
