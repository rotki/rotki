import type { DecodingProgress } from '../types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { setupSyncProgressMocks } from '../test-utils';
import DecodingProgressList from './DecodingProgressList.vue';

setupSyncProgressMocks();

describe('modules/sync-progress/components/DecodingProgressList', () => {
  let wrapper: VueWrapper<InstanceType<typeof DecodingProgressList>>;
  let pinia: Pinia;

  function createDecodingProgress(
    chain: string,
    processed: number,
    total: number,
  ): DecodingProgress {
    return {
      chain,
      processed,
      progress: total > 0 ? Math.round((processed / total) * 100) : 0,
      total,
    };
  }

  function createWrapper(decoding: DecodingProgress[]): VueWrapper<InstanceType<typeof DecodingProgressList>> {
    return mount(DecodingProgressList, {
      global: {
        plugins: [pinia],
        stubs: {
          DecodingProgressItem: {
            template: '<div data-testid="decoding-item" :data-chain="item.chain" :data-compact="String(compact === true)">{{ item.chain }}</div>',
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
        decoding,
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
    it('should show in-progress decoding by default', () => {
      const decoding = [
        createDecodingProgress('eth', 50, 100),
        createDecodingProgress('optimism', 100, 100),
      ];
      wrapper = createWrapper(decoding);

      const items = wrapper.findAll('[data-testid="decoding-item"]');
      expect(items).toHaveLength(1);
      expect(items[0].attributes('data-chain')).toBe('eth');
    });

    it('should not show completed decoding by default', () => {
      const decoding = [
        createDecodingProgress('eth', 100, 100),
        createDecodingProgress('optimism', 100, 100),
      ];
      wrapper = createWrapper(decoding);

      expect(wrapper.findAll('[data-testid="decoding-item"]')).toHaveLength(0);
    });
  });

  describe('completed section', () => {
    it('should show completed toggle button when there are completed decodings', () => {
      const decoding = [
        createDecodingProgress('eth', 50, 100),
        createDecodingProgress('optimism', 100, 100),
      ];
      wrapper = createWrapper(decoding);

      expect(wrapper.text()).toContain('sync_progress.completed_decoding');
    });

    it('should not show completed toggle when no completed decodings', () => {
      const decoding = [
        createDecodingProgress('eth', 50, 100),
        createDecodingProgress('optimism', 30, 100),
      ];
      wrapper = createWrapper(decoding);

      expect(wrapper.text()).not.toContain('sync_progress.completed_decoding');
    });

    it('should show completed decodings when toggle is clicked', async () => {
      const decoding = [
        createDecodingProgress('eth', 50, 100),
        createDecodingProgress('optimism', 100, 100),
      ];
      wrapper = createWrapper(decoding);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_decoding'));
      await toggleButton?.trigger('click');

      const items = wrapper.findAll('[data-testid="decoding-item"]');
      expect(items).toHaveLength(2);
    });

    it('should render completed decodings in compact mode', async () => {
      const decoding = [
        createDecodingProgress('eth', 50, 100),
        createDecodingProgress('optimism', 100, 100),
      ];
      wrapper = createWrapper(decoding);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_decoding'));
      await toggleButton?.trigger('click');

      const inProgressItem = wrapper.findAll('[data-testid="decoding-item"]').find(
        item => item.attributes('data-chain') === 'eth',
      );
      const completedItem = wrapper.findAll('[data-testid="decoding-item"]').find(
        item => item.attributes('data-chain') === 'optimism',
      );
      // In-progress items are not compact
      expect(inProgressItem?.attributes('data-compact')).toBe('false');
      // Completed items are rendered in compact mode
      expect(completedItem?.attributes('data-compact')).toBe('true');
    });
  });

  describe('empty state', () => {
    it('should render empty list when no decoding data', () => {
      wrapper = createWrapper([]);

      expect(wrapper.findAll('[data-testid="decoding-item"]')).toHaveLength(0);
    });
  });
});
