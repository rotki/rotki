import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AddressStatus, AddressSubtype, type ChainProgress } from '../types';
import ChainProgressList from './ChainProgressList.vue';

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    assetImageUrl: vi.fn(),
  }),
}));
vi.mock('@/services/websocket/websocket-service');

describe('modules/sync-progress/components/ChainProgressList', () => {
  let wrapper: VueWrapper<InstanceType<typeof ChainProgressList>>;
  let pinia: Pinia;

  function createChainProgress(
    chain: string,
    completed: number,
    total: number,
  ): ChainProgress {
    return {
      addresses: Array.from({ length: total }, (_, i) => ({
        address: `0x${chain}${i.toString().padStart(38, '0')}`,
        status: i < completed ? AddressStatus.COMPLETE : AddressStatus.PENDING,
        subtype: AddressSubtype.EVM,
      })),
      chain,
      completed,
      inProgress: 0,
      pending: total - completed,
      progress: total > 0 ? Math.round((completed / total) * 100) : 0,
      total,
    };
  }

  function createWrapper(chains: ChainProgress[]): VueWrapper<InstanceType<typeof ChainProgressList>> {
    return mount(ChainProgressList, {
      global: {
        plugins: [pinia],
        stubs: {
          ChainProgressItem: {
            template: '<div data-testid="chain-item" :data-chain="chain.chain" :data-compact="String(compact === true)">{{ chain.chain }}</div>',
            props: {
              chain: { type: Object, required: true },
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
        chains,
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
    it('should show in-progress chains by default', () => {
      const chains = [
        createChainProgress('eth', 1, 3),
        createChainProgress('optimism', 3, 3),
      ];
      wrapper = createWrapper(chains);

      const items = wrapper.findAll('[data-testid="chain-item"]');
      expect(items).toHaveLength(1);
      expect(items[0].attributes('data-chain')).toBe('eth');
    });

    it('should not show completed chains by default', () => {
      const chains = [
        createChainProgress('eth', 3, 3),
        createChainProgress('optimism', 3, 3),
      ];
      wrapper = createWrapper(chains);

      expect(wrapper.findAll('[data-testid="chain-item"]')).toHaveLength(0);
    });
  });

  describe('completed section', () => {
    it('should show completed toggle button when there are completed chains', () => {
      const chains = [
        createChainProgress('eth', 1, 3),
        createChainProgress('optimism', 3, 3),
      ];
      wrapper = createWrapper(chains);

      expect(wrapper.text()).toContain('sync_progress.completed_chains');
    });

    it('should not show completed toggle when no completed chains', () => {
      const chains = [
        createChainProgress('eth', 1, 3),
        createChainProgress('optimism', 1, 3),
      ];
      wrapper = createWrapper(chains);

      expect(wrapper.text()).not.toContain('sync_progress.completed_chains');
    });

    it('should show completed chains when toggle is clicked', async () => {
      const chains = [
        createChainProgress('eth', 1, 3),
        createChainProgress('optimism', 3, 3),
      ];
      wrapper = createWrapper(chains);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_chains'));
      await toggleButton?.trigger('click');

      const items = wrapper.findAll('[data-testid="chain-item"]');
      expect(items).toHaveLength(2);
    });

    it('should hide completed chains when toggle is clicked again', async () => {
      const chains = [
        createChainProgress('eth', 1, 3),
        createChainProgress('optimism', 3, 3),
      ];
      wrapper = createWrapper(chains);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_chains'));
      await toggleButton?.trigger('click');
      await toggleButton?.trigger('click');

      const items = wrapper.findAll('[data-testid="chain-item"]');
      expect(items).toHaveLength(1);
    });

    it('should render completed chains in compact mode', async () => {
      const chains = [
        createChainProgress('eth', 1, 3),
        createChainProgress('optimism', 3, 3),
      ];
      wrapper = createWrapper(chains);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_chains'));
      await toggleButton?.trigger('click');

      const inProgressItem = wrapper.findAll('[data-testid="chain-item"]').find(
        item => item.attributes('data-chain') === 'eth',
      );
      const completedItem = wrapper.findAll('[data-testid="chain-item"]').find(
        item => item.attributes('data-chain') === 'optimism',
      );
      // In-progress items are not compact
      expect(inProgressItem?.attributes('data-compact')).toBe('false');
      // Completed items are rendered in compact mode
      expect(completedItem?.attributes('data-compact')).toBe('true');
    });
  });

  describe('chevron icons', () => {
    it('should show chevron down when completed section is collapsed', () => {
      const chains = [
        createChainProgress('eth', 1, 3),
        createChainProgress('optimism', 3, 3),
      ];
      wrapper = createWrapper(chains);

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-chevron-down')).toBe(true);
    });

    it('should show chevron up when completed section is expanded', async () => {
      const chains = [
        createChainProgress('eth', 1, 3),
        createChainProgress('optimism', 3, 3),
      ];
      wrapper = createWrapper(chains);

      const buttons = wrapper.findAll('button');
      const toggleButton = buttons.find(btn => btn.text().includes('sync_progress.completed_chains'));
      await toggleButton?.trigger('click');

      const icons = wrapper.findAll('[data-testid="icon"]');
      expect(icons.some(icon => icon.text() === 'lu-chevron-up')).toBe(true);
    });
  });

  describe('empty state', () => {
    it('should render empty list when no chains', () => {
      wrapper = createWrapper([]);

      expect(wrapper.findAll('[data-testid="chain-item"]')).toHaveLength(0);
    });
  });
});
