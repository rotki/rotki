import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AddressStatus, AddressSubtype, type ChainProgress } from '../types';
import ChainProgressItem from './ChainProgressItem.vue';

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    assetImageUrl: vi.fn(),
  }),
}));
vi.mock('@/services/websocket/websocket-service');

describe('modules/sync-progress/components/ChainProgressItem', () => {
  let wrapper: VueWrapper<InstanceType<typeof ChainProgressItem>>;
  let pinia: Pinia;

  function createChainProgress(
    completed: number,
    total: number,
    inProgress = 0,
    chain = 'eth',
  ): ChainProgress {
    const addresses = [];
    for (let i = 0; i < total; i++) {
      let status: AddressStatus;
      if (i < completed) {
        status = AddressStatus.COMPLETE;
      }
      else if (i < completed + inProgress) {
        status = AddressStatus.QUERYING;
      }
      else {
        status = AddressStatus.PENDING;
      }
      addresses.push({
        address: `0x${i.toString().padStart(40, '0')}`,
        status,
        subtype: AddressSubtype.EVM,
      });
    }

    return {
      addresses,
      chain,
      completed,
      inProgress,
      pending: total - completed - inProgress,
      progress: total > 0 ? Math.round((completed / total) * 100) : 0,
      total,
    };
  }

  function createWrapper(chain: ChainProgress, compact = false): VueWrapper<InstanceType<typeof ChainProgressItem>> {
    return mount(ChainProgressItem, {
      global: {
        plugins: [pinia],
        stubs: {
          AddressProgressItem: {
            template: '<div data-testid="address-item">{{ address.address }}</div>',
            props: ['address', 'chain', 'compact'],
          },
          ChainIcon: {
            template: '<span data-testid="chain-icon">{{ chain }}</span>',
            props: ['chain', 'size'],
          },
          RuiIcon: {
            template: '<span data-testid="icon" :class="[$attrs.class]">{{ name }}</span>',
            props: ['name', 'size'],
          },
          RuiProgress: {
            template: '<div data-testid="progress" :data-value="value"></div>',
            props: ['value', 'color', 'size', 'rounded'],
          },
        },
      },
      props: {
        chain,
        compact,
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
    it('should show check icon when all addresses are complete', () => {
      const chain = createChainProgress(3, 3, 0);
      wrapper = createWrapper(chain);

      const icons = wrapper.findAll('[data-testid="icon"]');
      const checkIcon = icons.find(icon => icon.text() === 'lu-check');
      expect(checkIcon).toBeDefined();
      expect(checkIcon?.classes()).toContain('text-rui-success');
    });

    it('should show loader icon when there is activity', () => {
      const chain = createChainProgress(1, 3, 1);
      wrapper = createWrapper(chain);

      const icons = wrapper.findAll('[data-testid="icon"]');
      const loaderIcon = icons.find(icon => icon.text() === 'lu-loader-circle');
      expect(loaderIcon).toBeDefined();
      expect(loaderIcon?.classes()).toContain('text-rui-primary');
      expect(loaderIcon?.classes()).toContain('animate-spin');
    });

    it('should display progress counts', () => {
      const chain = createChainProgress(2, 5, 1);
      wrapper = createWrapper(chain);

      expect(wrapper.text()).toContain('2/5');
    });
  });

  describe('progress bar', () => {
    it('should show progress bar when not complete', () => {
      const chain = createChainProgress(2, 5, 1);
      wrapper = createWrapper(chain);

      const progress = wrapper.find('[data-testid="progress"]');
      expect(progress.exists()).toBe(true);
      expect(progress.attributes('data-value')).toBe('40');
    });

    it('should hide progress bar when complete', () => {
      const chain = createChainProgress(5, 5, 0);
      wrapper = createWrapper(chain);

      expect(wrapper.find('[data-testid="progress"]').exists()).toBe(false);
    });
  });

  describe('expand/collapse', () => {
    it('should be collapsed by default', () => {
      const chain = createChainProgress(1, 3, 1);
      wrapper = createWrapper(chain);

      expect(wrapper.findAll('[data-testid="address-item"]')).toHaveLength(0);
    });

    it('should expand when button is clicked', async () => {
      const chain = createChainProgress(1, 3, 1);
      wrapper = createWrapper(chain);

      await wrapper.find('button').trigger('click');

      expect(wrapper.findAll('[data-testid="address-item"]').length).toBeGreaterThan(0);
    });

    it('should collapse when button is clicked again', async () => {
      const chain = createChainProgress(1, 3, 1);
      wrapper = createWrapper(chain);

      await wrapper.find('button').trigger('click');
      expect(wrapper.findAll('[data-testid="address-item"]').length).toBeGreaterThan(0);

      await wrapper.find('button').trigger('click');
      expect(wrapper.findAll('[data-testid="address-item"]')).toHaveLength(0);
    });

    it('should show chevron down when collapsed', () => {
      const chain = createChainProgress(1, 3, 1);
      wrapper = createWrapper(chain);

      const icons = wrapper.findAll('[data-testid="icon"]');
      const chevronIcon = icons.find(icon => icon.text() === 'lu-chevron-down');
      expect(chevronIcon).toBeDefined();
    });

    it('should show chevron up when expanded', async () => {
      const chain = createChainProgress(1, 3, 1);
      wrapper = createWrapper(chain);

      await wrapper.find('button').trigger('click');

      const icons = wrapper.findAll('[data-testid="icon"]');
      const chevronIcon = icons.find(icon => icon.text() === 'lu-chevron-up');
      expect(chevronIcon).toBeDefined();
    });
  });

  describe('show more functionality', () => {
    it('should limit visible addresses to 5 initially', async () => {
      const chain = createChainProgress(0, 10, 2);
      wrapper = createWrapper(chain);

      await wrapper.find('button').trigger('click');

      expect(wrapper.findAll('[data-testid="address-item"]')).toHaveLength(5);
    });

    it('should show "show more" button when there are more addresses', async () => {
      const chain = createChainProgress(0, 10, 2);
      wrapper = createWrapper(chain);

      await wrapper.find('button').trigger('click');

      expect(wrapper.text()).toContain('sync_progress.show_more');
    });

    it('should not show "show more" button when 5 or fewer addresses', async () => {
      const chain = createChainProgress(0, 5, 2);
      wrapper = createWrapper(chain);

      await wrapper.find('button').trigger('click');

      expect(wrapper.text()).not.toContain('sync_progress.show_more');
    });

    it('should show all addresses when "show more" is clicked', async () => {
      const chain = createChainProgress(0, 10, 2);
      wrapper = createWrapper(chain);

      await wrapper.find('button').trigger('click');
      const showMoreButton = wrapper.findAll('button').find(btn => btn.text().includes('sync_progress.show_more'));
      await showMoreButton?.trigger('click');

      expect(wrapper.findAll('[data-testid="address-item"]')).toHaveLength(10);
    });
  });

  describe('border styling', () => {
    it('should apply success border when complete', () => {
      const chain = createChainProgress(5, 5, 0);
      wrapper = createWrapper(chain);

      expect(wrapper.classes()).toContain('border-l-rui-success');
    });

    it('should apply primary border when has activity', () => {
      const chain = createChainProgress(1, 5, 2);
      wrapper = createWrapper(chain);

      expect(wrapper.classes()).toContain('border-l-rui-primary');
    });
  });

  describe('chain display', () => {
    it('should display chain icon', () => {
      const chain = createChainProgress(1, 3, 1, 'optimism');
      wrapper = createWrapper(chain);

      const chainIcon = wrapper.find('[data-testid="chain-icon"]');
      expect(chainIcon.exists()).toBe(true);
      expect(chainIcon.text()).toBe('optimism');
    });
  });
});
