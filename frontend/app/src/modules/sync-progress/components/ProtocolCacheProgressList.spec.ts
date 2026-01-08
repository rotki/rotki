import type { ProtocolCacheProgress } from '../types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { setupSyncProgressMocks } from '../test-utils';
import ProtocolCacheProgressList from './ProtocolCacheProgressList.vue';

setupSyncProgressMocks();

describe('modules/sync-progress/components/ProtocolCacheProgressList', () => {
  let wrapper: VueWrapper<InstanceType<typeof ProtocolCacheProgressList>>;
  let pinia: Pinia;

  function createProtocolCacheProgress(
    chain: string,
    protocol: string,
    processed: number,
    total: number,
  ): ProtocolCacheProgress {
    return {
      chain,
      processed,
      progress: total > 0 ? Math.round((processed / total) * 100) : 0,
      protocol,
      total,
    };
  }

  function createWrapper(protocolCache: ProtocolCacheProgress[]): VueWrapper<InstanceType<typeof ProtocolCacheProgressList>> {
    return mount(ProtocolCacheProgressList, {
      global: {
        plugins: [pinia],
        stubs: {
          ProtocolCacheProgressItem: {
            template: '<div data-testid="protocol-cache-item" :data-chain="item.chain" :data-protocol="item.protocol" :data-compact="String(compact === true)">{{ item.chain }}-{{ item.protocol }}</div>',
            props: {
              item: { type: Object, required: true },
              compact: { type: Boolean, default: false },
            },
          },
          RuiIcon: {
            template: '<span data-testid="icon">{{ name }}</span>',
            props: ['name', 'size'],
          },
        },
      },
      props: {
        protocolCache,
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

  describe('filtering', () => {
    it('should show in-progress protocol cache by default', () => {
      const protocolCache = [
        createProtocolCacheProgress('eth', 'uniswap_v3', 50, 100),
        createProtocolCacheProgress('optimism', 'velodrome', 100, 100),
      ];
      wrapper = createWrapper(protocolCache);

      const items = wrapper.findAll('[data-testid="protocol-cache-item"]');
      expect(items).toHaveLength(1);
      expect(items[0].attributes('data-chain')).toBe('eth');
      expect(items[0].attributes('data-protocol')).toBe('uniswap_v3');
    });

    it('should not show completed protocol cache by default', () => {
      const protocolCache = [
        createProtocolCacheProgress('eth', 'uniswap_v3', 100, 100),
        createProtocolCacheProgress('optimism', 'velodrome', 100, 100),
      ];
      wrapper = createWrapper(protocolCache);

      expect(wrapper.findAll('[data-testid="protocol-cache-item"]')).toHaveLength(0);
    });
  });

  describe('completed section', () => {
    it('should show completed toggle button when there are completed items', () => {
      const protocolCache = [
        createProtocolCacheProgress('eth', 'uniswap_v3', 50, 100),
        createProtocolCacheProgress('optimism', 'velodrome', 100, 100),
      ];
      wrapper = createWrapper(protocolCache);

      expect(wrapper.text()).toContain('sync_progress.completed_protocol_cache');
    });

    it('should not show completed toggle when no completed items', () => {
      const protocolCache = [
        createProtocolCacheProgress('eth', 'uniswap_v3', 50, 100),
        createProtocolCacheProgress('optimism', 'velodrome', 30, 100),
      ];
      wrapper = createWrapper(protocolCache);

      expect(wrapper.text()).not.toContain('sync_progress.completed_protocol_cache');
    });

    it('should show completed items when toggle is clicked', async () => {
      const protocolCache = [
        createProtocolCacheProgress('eth', 'uniswap_v3', 50, 100),
        createProtocolCacheProgress('optimism', 'velodrome', 100, 100),
      ];
      wrapper = createWrapper(protocolCache);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_protocol_cache'));
      await toggleButton?.trigger('click');

      const items = wrapper.findAll('[data-testid="protocol-cache-item"]');
      expect(items).toHaveLength(2);
    });

    it('should render completed items in compact mode', async () => {
      const protocolCache = [
        createProtocolCacheProgress('eth', 'uniswap_v3', 50, 100),
        createProtocolCacheProgress('optimism', 'velodrome', 100, 100),
      ];
      wrapper = createWrapper(protocolCache);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_protocol_cache'));
      await toggleButton?.trigger('click');

      const inProgressItem = wrapper.findAll('[data-testid="protocol-cache-item"]').find(
        item => item.attributes('data-chain') === 'eth',
      );
      const completedItem = wrapper.findAll('[data-testid="protocol-cache-item"]').find(
        item => item.attributes('data-chain') === 'optimism',
      );
      // In-progress items are not compact
      expect(inProgressItem?.attributes('data-compact')).toBe('false');
      // Completed items are rendered in compact mode
      expect(completedItem?.attributes('data-compact')).toBe('true');
    });
  });

  describe('empty state', () => {
    it('should render empty list when no protocol cache data', () => {
      wrapper = createWrapper([]);

      expect(wrapper.findAll('[data-testid="protocol-cache-item"]')).toHaveLength(0);
    });
  });
});
