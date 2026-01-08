import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type AddressProgress, AddressStatus, AddressStep, AddressSubtype } from '../types';
import AddressProgressItem from './AddressProgressItem.vue';

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    assetImageUrl: vi.fn(),
  }),
}));
vi.mock('@/services/websocket/websocket-service');

describe('modules/sync-progress/components/AddressProgressItem', () => {
  let wrapper: VueWrapper<InstanceType<typeof AddressProgressItem>>;
  let pinia: Pinia;

  function createAddress(
    status: AddressStatus,
    options: Partial<AddressProgress> = {},
  ): AddressProgress {
    return {
      address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
      status,
      subtype: AddressSubtype.EVM,
      ...options,
    };
  }

  function createWrapper(address: AddressProgress, chain = 'eth', compact = false): VueWrapper<InstanceType<typeof AddressProgressItem>> {
    return mount(AddressProgressItem, {
      global: {
        plugins: [pinia],
        stubs: {
          DateDisplay: true,
          HashLink: {
            template: '<span data-testid="hash-link">{{ text }}</span>',
            props: ['text', 'location'],
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
        address,
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
    it('should display complete status and check icon for completed addresses', () => {
      const address = createAddress(AddressStatus.COMPLETE);
      wrapper = createWrapper(address);

      // Check translation key is used (sync_progress.status.complete)
      expect(wrapper.text()).toContain('sync_progress.status.complete');
      expect(wrapper.find('[data-testid="icon"]').text()).toBe('lu-check');
    });

    it('should display pending status and circle icon for pending addresses', () => {
      const address = createAddress(AddressStatus.PENDING);
      wrapper = createWrapper(address);

      expect(wrapper.text()).toContain('sync_progress.status.pending');
      expect(wrapper.find('[data-testid="icon"]').text()).toBe('lu-circle');
    });

    it('should display decoding status and loader icon for decoding addresses', () => {
      const address = createAddress(AddressStatus.DECODING);
      wrapper = createWrapper(address);

      expect(wrapper.text()).toContain('sync_progress.status.decoding');
      expect(wrapper.find('[data-testid="icon"]').text()).toBe('lu-loader-circle');
    });

    it('should display step-specific querying status', () => {
      const transactionsAddress = createAddress(AddressStatus.QUERYING, { step: AddressStep.TRANSACTIONS });
      wrapper = createWrapper(transactionsAddress);
      expect(wrapper.text()).toContain('sync_progress.status.querying_transactions');
      wrapper.unmount();

      const internalAddress = createAddress(AddressStatus.QUERYING, { step: AddressStep.INTERNAL });
      wrapper = createWrapper(internalAddress);
      expect(wrapper.text()).toContain('sync_progress.status.querying_internal');
      wrapper.unmount();

      const tokensAddress = createAddress(AddressStatus.QUERYING, { step: AddressStep.TOKENS });
      wrapper = createWrapper(tokensAddress);
      expect(wrapper.text()).toContain('sync_progress.status.querying_tokens');
    });
  });

  describe('icon styling', () => {
    it('should apply success color for completed addresses', () => {
      const address = createAddress(AddressStatus.COMPLETE);
      wrapper = createWrapper(address);

      const icon = wrapper.find('[data-testid="icon"]');
      expect(icon.classes()).toContain('text-rui-success');
    });

    it('should apply primary color and animation for querying addresses', () => {
      const address = createAddress(AddressStatus.QUERYING);
      wrapper = createWrapper(address);

      const icon = wrapper.find('[data-testid="icon"]');
      expect(icon.classes()).toContain('text-rui-primary');
      expect(icon.classes()).toContain('animate-spin');
    });

    it('should apply disabled color for pending addresses', () => {
      const address = createAddress(AddressStatus.PENDING);
      wrapper = createWrapper(address);

      const icon = wrapper.find('[data-testid="icon"]');
      expect(icon.classes()).toContain('text-rui-text-disabled');
    });
  });

  describe('period progress', () => {
    it('should show progress bar when address has period progress', () => {
      const address = createAddress(AddressStatus.QUERYING, {
        period: [0, 500],
        originalPeriodEnd: 1000,
        periodProgress: 50,
      });
      wrapper = createWrapper(address);

      const progress = wrapper.find('[data-testid="progress"]');
      expect(progress.exists()).toBe(true);
      expect(progress.attributes('data-value')).toBe('50');
    });

    it('should not show progress bar for bitcoin addresses', () => {
      const address = createAddress(AddressStatus.QUERYING, {
        period: [0, 500],
        periodProgress: 50,
        subtype: AddressSubtype.BITCOIN,
      });
      wrapper = createWrapper(address);

      expect(wrapper.find('[data-testid="progress"]').exists()).toBe(false);
    });

    it('should not show progress bar in compact mode', () => {
      const address = createAddress(AddressStatus.QUERYING, {
        period: [0, 500],
        periodProgress: 50,
      });
      wrapper = createWrapper(address, 'eth', true);

      expect(wrapper.find('[data-testid="progress"]').exists()).toBe(false);
    });
  });

  describe('address display', () => {
    it('should display the address through HashLink', () => {
      const address = createAddress(AddressStatus.PENDING);
      wrapper = createWrapper(address, 'optimism');

      const hashLink = wrapper.find('[data-testid="hash-link"]');
      expect(hashLink.exists()).toBe(true);
      expect(hashLink.text()).toContain('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c');
    });
  });

  describe('visual feedback', () => {
    it('should animate for querying addresses', () => {
      const address = createAddress(AddressStatus.QUERYING);
      wrapper = createWrapper(address);

      expect(wrapper.classes()).toContain('animate-pulse');
    });

    it('should not animate for complete addresses', () => {
      const address = createAddress(AddressStatus.COMPLETE);
      wrapper = createWrapper(address);

      expect(wrapper.classes()).not.toContain('animate-pulse');
    });
  });
});
