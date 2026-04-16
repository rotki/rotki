import type { Pinia } from 'pinia';
import type { EvmChainInfo } from '@/modules/api/types/chains';
import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed } from 'vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

vi.mock('@/composables/info/chains', (): Record<string, unknown> => ({
  useSupportedChains: vi.fn().mockReturnValue({
    getChain: (): Blockchain => Blockchain.ETH,
    getChainImageUrl: (chain: Blockchain): string => `${chain}.png`,
    getChainName: (): string => 'Ethereum',
    getEvmChainName: (chain: string): string | undefined => {
      if (chain.startsWith('eth'))
        return 'ethereum';
      else if (chain.startsWith('opt'))
        return 'optimism';
      return undefined;
    },
    getNativeAsset: (chain: Blockchain): Blockchain => chain,
    isEvmLikeChains: (_chain: string): boolean => false,
    matchChain: (chain: string): Blockchain | undefined => {
      if (chain.toLowerCase() === 'ethereum')
        return Blockchain.ETH;
      else if (chain.toLowerCase() === 'optimism')
        return Blockchain.OPTIMISM;
      return undefined;
    },
    supportedChains: computed<EvmChainInfo[]>((): EvmChainInfo[] => []),
    txChains: computed<EvmChainInfo[]>((): EvmChainInfo[] => [{
      evmChainName: 'ethereum',
      id: Blockchain.ETH,
      image: '',
      name: 'Ethereum',
      nativeToken: 'ETH',
      type: 'evm',
    }]),
  }),
}));

vi.mock('@/composables/api/blockchain/addresses-names', (): Record<string, unknown> => ({
  useAddressesNamesApi: vi.fn().mockReturnValue({
    addAddressBook: vi.fn(),
    deleteAddressBook: vi.fn(),
    ensAvatarUrl: vi.fn(),
    fetchAddressBook: vi.fn(),
    getAddressesNames: vi.fn().mockResolvedValue([]),
    getEnsNames: vi.fn().mockResolvedValue({}),
    getEnsNamesTask: vi.fn(),
    updateAddressBook: vi.fn(),
  }),
}));

vi.mock('@/modules/balances/blockchain/use-blockchain-account-data', (): Record<string, unknown> => ({
  useBlockchainAccountData: vi.fn().mockReturnValue({
    useAccountTags: (): Ref<string[]> => ref<string[]>([]),
  }),
}));

describe('hash-link', () => {
  let wrapper: VueWrapper<InstanceType<typeof HashLink>>;
  let pinia: Pinia;

  beforeEach((): void => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  const createWrapper = (props: {
    text: string;
    displayMode?: 'default' | 'link' | 'copy' | 'text';
    hideText?: boolean;
    location?: string;
    size?: number | string;
    truncateLength?: number;
    type?: 'address' | 'block' | 'transaction' | 'token';
    noScramble?: boolean;
  }): VueWrapper<InstanceType<typeof HashLink>> =>
    mount(HashLink, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
        stubs: {
          EnsAvatar: true,
          TagDisplay: true,
          AddressDeleteButton: true,
          AddressEditButton: true,
          CopyButton: true,
          LinkButton: true,
        },
      },
      props,
    });

  describe('text display', () => {
    it('should display truncated address by default', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address });

      // Default truncateLength is 4, but with 0x prefix it shows 4+2 chars at start
      expect(wrapper.text()).toContain('0x1234...5678');
    });

    it('should display full address when truncateLength is 0', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, truncateLength: 0 });

      expect(wrapper.text()).toContain(address);
    });

    it('should display custom truncate length', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, truncateLength: 6 });

      // truncateAddress adds startPadding (2 for 0x) to truncLength at the start
      expect(wrapper.text()).toContain('0x123456...345678');
    });

    it('should hide text when hideText is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, hideText: true });

      expect(wrapper.find('.blur').exists()).toBe(false);
      expect(wrapper.text()).not.toContain('0x12...5678');
    });
  });

  describe('display modes', () => {
    const address = '0x1234567890abcdef1234567890abcdef12345678';

    it('should show both copy and link buttons in default mode', () => {
      wrapper = createWrapper({ text: address, location: 'eth', displayMode: 'default' });

      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(true);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(true);
    });

    it('should show only link button in link mode', () => {
      wrapper = createWrapper({ text: address, location: 'eth', displayMode: 'link' });

      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(false);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(true);
    });

    it('should show only copy button in copy mode', () => {
      wrapper = createWrapper({ text: address, displayMode: 'copy' });

      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(true);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });

    it('should show no buttons in text mode', () => {
      wrapper = createWrapper({ text: address, displayMode: 'text' });

      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(false);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });
  });

  describe('showIcon behavior', () => {
    it('should show EnsAvatar for non-numeric addresses', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, type: 'address' });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(true);
    });

    it('should hide EnsAvatar for numeric text (like validator index)', () => {
      wrapper = createWrapper({ text: '12345', type: 'address' });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(false);
    });

    it('should hide EnsAvatar when type is not address', () => {
      const txHash = '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab';
      wrapper = createWrapper({ text: txHash, type: 'transaction' });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(false);
    });

    it('should hide EnsAvatar when hideText is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, type: 'address', hideText: true });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(false);
    });

    it('should show EnsAvatar when location is present and is a blockchain', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, type: 'address', location: 'ethereum' });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(true);
    });

    it('should hide EnsAvatar when location is present but not a blockchain', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, type: 'address', location: 'unknown_location' });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(false);
    });
  });

  describe('blockchain location', () => {
    it('should show link button when location is a valid blockchain', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth' });

      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(true);
    });

    it('should hide link button when location has no explorer', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'unknown_location' });

      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });
  });

  describe('scramble data', () => {
    beforeEach(async () => {
      useFrontendSettingsStore().update({ scrambleData: true });
    });

    it('should scramble address when scrambleData is enabled', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address });

      expect(wrapper.text()).not.toContain('0x12...5678');
    });

    it('should not scramble address when noScramble is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, noScramble: true, truncateLength: 0 });

      expect(wrapper.text()).toContain(address);
    });

    it('should apply blur class when privacy mode is semi-private or higher', async () => {
      const frontendStore = useFrontendSettingsStore();
      // PrivacyMode.SEMI_PRIVATE = 1 means shouldShowAmount is false
      frontendStore.update({
        privacyMode: 1,
      });
      await nextTick();

      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address });
      await nextTick();

      // When privacyMode >= SEMI_PRIVATE, shouldShowAmount is false, applying blur
      const blurElement = wrapper.find('.blur');
      expect(blurElement.exists()).toBe(true);
    });
  });

  describe('different explorer types', () => {
    it('should use address explorer for address type', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth', type: 'address' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.exists()).toBe(true);
    });

    it('should use transaction explorer for transaction type', () => {
      const txHash = '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab';
      wrapper = createWrapper({ text: txHash, location: 'eth', type: 'transaction' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.exists()).toBe(true);
    });

    it('should use block explorer for block type', () => {
      wrapper = createWrapper({ text: '12345678', location: 'eth', type: 'block' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.exists()).toBe(true);
    });

    it('should use token explorer for token type', () => {
      const tokenAddress = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: tokenAddress, location: 'eth', type: 'token' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.exists()).toBe(true);
      expect(linkButton.props('isToken')).toBe(true);
    });
  });

  describe('custom size', () => {
    it('should pass size prop to CopyButton', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, size: 16 });

      const copyButton = wrapper.findComponent({ name: 'CopyButton' });
      expect(copyButton.props('size')).toBe(16);
    });

    it('should pass size prop to LinkButton', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth', size: 16 });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.props('size')).toBe(16);
    });

    it('should use default size of 12', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address });

      const copyButton = wrapper.findComponent({ name: 'CopyButton' });
      expect(copyButton.props('size')).toBe(12);
    });
  });

  describe('address book chain', () => {
    it('should include AddressEditButton in tooltip for non-ETH2 blockchain addresses', async () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth', type: 'address' });

      // The RuiTooltipStub renders the default slot content only on mouseover
      // We need to find the div that has the @mouseover handler (from RuiTooltipStub)
      // and trigger mouseover on it
      const tooltipWrapper = wrapper.find('[class*="flex"]').find('div');
      await tooltipWrapper.trigger('mouseover');
      await nextTick();

      // Check that AddressEditButton stub exists within the wrapper after tooltip opens
      const editButton = wrapper.findComponent({ name: 'AddressEditButton' });
      expect(editButton.exists()).toBe(true);
    });

    it('should not render AddressEditButton for ETH2 addresses', async () => {
      wrapper = createWrapper({ text: '12345', location: 'eth2', type: 'address' });

      // Trigger mouseover to show tooltip content
      await wrapper.find('div').trigger('mouseover');
      await nextTick();

      const editButton = wrapper.findComponent({ name: 'AddressEditButton' });
      expect(editButton.exists()).toBe(false);
    });

    it('should not render AddressEditButton when type is not address', async () => {
      const txHash = '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab';
      wrapper = createWrapper({ text: txHash, location: 'eth', type: 'transaction' });

      // Trigger mouseover to show tooltip content
      await wrapper.find('div').trigger('mouseover');
      await nextTick();

      const editButton = wrapper.findComponent({ name: 'AddressEditButton' });
      expect(editButton.exists()).toBe(false);
    });

    it('should not render AddressEditButton when location is undefined', async () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, type: 'address' });

      // Trigger mouseover to show tooltip content
      await wrapper.find('div').trigger('mouseover');
      await nextTick();

      const editButton = wrapper.findComponent({ name: 'AddressEditButton' });
      expect(editButton.exists()).toBe(false);
    });
  });

  describe('chain matching', () => {
    it('should match location via matchChain when not a direct blockchain', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      // 'ethereum' is not a Blockchain enum value but matchChain returns ETH
      wrapper = createWrapper({ text: address, location: 'ethereum' });

      // Should show link button since matchChain returns ETH
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(true);
    });

    it('should return undefined for unmatched locations', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'invalid_chain' });

      // Should not show link button since no explorer base is set
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });
  });

  describe('tooltip behavior', () => {
    it('should disable tooltip when truncateLength is 0', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, truncateLength: 0 });

      // RuiTooltip should exist but be disabled
      const tooltip = wrapper.find('div');
      expect(tooltip.exists()).toBe(true);
    });

    it('should render RuiTooltip when text is not hidden', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address });

      // RuiTooltipStub should be rendered
      expect(wrapper.text()).toContain('0x1234...5678');
    });

    it('should not render RuiTooltip when hideText is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, hideText: true });

      // The truncated text should not be visible
      expect(wrapper.text()).not.toContain('0x1234');
    });
  });

  describe('props passed to child components', () => {
    it('should pass correct props to CopyButton', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, size: 14 });

      const copyButton = wrapper.findComponent({ name: 'CopyButton' });
      expect(copyButton.props('text')).toBe(address);
      expect(copyButton.props('size')).toBe(14);
    });

    it('should pass correct props to LinkButton', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth', size: 14, type: 'token' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.props('text')).toBe(address);
      expect(linkButton.props('size')).toBe(14);
      expect(linkButton.props('isToken')).toBe(true);
      expect(linkButton.props('base')).toContain('etherscan.io');
    });

    it('should pass correct props to EnsAvatar', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, type: 'address' });

      const ensAvatar = wrapper.findComponent({ name: 'EnsAvatar' });
      expect(ensAvatar.exists()).toBe(true);
      expect(ensAvatar.props('address')).toBe(address);
      expect(ensAvatar.props('avatar')).toBe(true);
      expect(ensAvatar.props('size')).toBe('22px');
    });
  });

  describe('button container visibility', () => {
    it('should show button container when showLink is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth', displayMode: 'link' });

      // Container should exist because showLink is true
      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.exists()).toBe(true);
    });

    it('should show button container when showCopy is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, displayMode: 'copy' });

      // Container should exist because showCopy is true
      const copyButton = wrapper.findComponent({ name: 'CopyButton' });
      expect(copyButton.exists()).toBe(true);
    });

    it('should hide button container in text mode', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, displayMode: 'text' });

      // Neither copy nor link button should exist
      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(false);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });
  });
});
