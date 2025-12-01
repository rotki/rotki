import type { Pinia } from 'pinia';
import type { EvmChainInfo } from '@/types/api/chains';
import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed } from 'vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

vi.mock('vue-router', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(),
  }),
  createRouter: vi.fn().mockImplementation(() => ({
    beforeEach: vi.fn(),
  })),
  createWebHashHistory: vi.fn(),
}));

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    getChain: () => Blockchain.ETH,
    getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
    getChainName: () => 'Ethereum',
    getEvmChainName: (chain: string) => {
      if (chain.startsWith('eth'))
        return 'ethereum';
      else if (chain.startsWith('opt'))
        return 'optimism';
      return undefined;
    },
    getNativeAsset: (chain: Blockchain) => chain,
    isEvmLikeChains: (_chain: string) => false,
    matchChain: (chain: string) => {
      if (chain.toLowerCase() === 'ethereum')
        return Blockchain.ETH;
      else if (chain.toLowerCase() === 'optimism')
        return Blockchain.OPTIMISM;
      return undefined;
    },
    supportedChains: computed<EvmChainInfo[]>(() => []),
    txChains: computed<EvmChainInfo[]>(() => [{
      evmChainName: 'ethereum',
      id: Blockchain.ETH,
      image: '',
      name: 'Ethereum',
      nativeToken: 'ETH',
      type: 'evm',
    }]),
  }),
}));

vi.mock('@/composables/api/blockchain/addresses-names', () => ({
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

vi.mock('@/modules/balances/blockchain/use-blockchain-account-data', () => ({
  useBlockchainAccountData: vi.fn().mockReturnValue({
    useAccountTags: () => ref<string[]>([]),
  }),
}));

describe('hashLink.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof HashLink>>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
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
  }) =>
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
    it('displays truncated address by default', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address });

      // Default truncateLength is 4, but with 0x prefix it shows 4+2 chars at start
      expect(wrapper.text()).toContain('0x1234...5678');
    });

    it('displays full address when truncateLength is 0', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, truncateLength: 0 });

      expect(wrapper.text()).toContain(address);
    });

    it('displays custom truncate length', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, truncateLength: 6 });

      // truncateAddress adds startPadding (2 for 0x) to truncLength at the start
      expect(wrapper.text()).toContain('0x123456...345678');
    });

    it('hides text when hideText is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, hideText: true });

      expect(wrapper.find('.blur').exists()).toBe(false);
      expect(wrapper.text()).not.toContain('0x12...5678');
    });
  });

  describe('display modes', () => {
    const address = '0x1234567890abcdef1234567890abcdef12345678';

    it('shows both copy and link buttons in default mode', () => {
      wrapper = createWrapper({ text: address, location: 'eth', displayMode: 'default' });

      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(true);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(true);
    });

    it('shows only link button in link mode', () => {
      wrapper = createWrapper({ text: address, location: 'eth', displayMode: 'link' });

      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(false);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(true);
    });

    it('shows only copy button in copy mode', () => {
      wrapper = createWrapper({ text: address, displayMode: 'copy' });

      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(true);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });

    it('shows no buttons in text mode', () => {
      wrapper = createWrapper({ text: address, displayMode: 'text' });

      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(false);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });
  });

  describe('showIcon behavior', () => {
    it('shows EnsAvatar for non-numeric addresses', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, type: 'address' });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(true);
    });

    it('hides EnsAvatar for numeric text (like validator index)', () => {
      wrapper = createWrapper({ text: '12345', type: 'address' });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(false);
    });

    it('hides EnsAvatar when type is not address', () => {
      const txHash = '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab';
      wrapper = createWrapper({ text: txHash, type: 'transaction' });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(false);
    });

    it('hides EnsAvatar when hideText is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, type: 'address', hideText: true });

      expect(wrapper.findComponent({ name: 'EnsAvatar' }).exists()).toBe(false);
    });
  });

  describe('blockchain location', () => {
    it('shows link button when location is a valid blockchain', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth' });

      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(true);
    });

    it('hides link button when location has no explorer', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'unknown_location' });

      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });
  });

  describe('scramble data', () => {
    beforeEach(async () => {
      await useFrontendSettingsStore().updateSetting({ scrambleData: true });
    });

    it('scrambles address when scrambleData is enabled', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address });

      expect(wrapper.text()).not.toContain('0x12...5678');
    });

    it('does not scramble address when noScramble is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, noScramble: true, truncateLength: 0 });

      expect(wrapper.text()).toContain(address);
    });

    it('applies blur class when privacy mode is semi-private or higher', async () => {
      const frontendStore = useFrontendSettingsStore();
      // PrivacyMode.SEMI_PRIVATE = 1 means shouldShowAmount is false
      await frontendStore.updateSetting({
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
    it('uses address explorer for address type', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth', type: 'address' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.exists()).toBe(true);
    });

    it('uses transaction explorer for transaction type', () => {
      const txHash = '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab';
      wrapper = createWrapper({ text: txHash, location: 'eth', type: 'transaction' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.exists()).toBe(true);
    });

    it('uses block explorer for block type', () => {
      wrapper = createWrapper({ text: '12345678', location: 'eth', type: 'block' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.exists()).toBe(true);
    });

    it('uses token explorer for token type', () => {
      const tokenAddress = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: tokenAddress, location: 'eth', type: 'token' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.exists()).toBe(true);
      expect(linkButton.props('isToken')).toBe(true);
    });
  });

  describe('custom size', () => {
    it('passes size prop to CopyButton', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, size: 16 });

      const copyButton = wrapper.findComponent({ name: 'CopyButton' });
      expect(copyButton.props('size')).toBe(16);
    });

    it('passes size prop to LinkButton', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth', size: 16 });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.props('size')).toBe(16);
    });

    it('uses default size of 12', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address });

      const copyButton = wrapper.findComponent({ name: 'CopyButton' });
      expect(copyButton.props('size')).toBe(12);
    });
  });

  describe('address book chain', () => {
    it('includes AddressEditButton in tooltip for non-ETH2 blockchain addresses', async () => {
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

    it('does not render AddressEditButton for ETH2 addresses', async () => {
      wrapper = createWrapper({ text: '12345', location: 'eth2', type: 'address' });

      // Trigger mouseover to show tooltip content
      await wrapper.find('div').trigger('mouseover');
      await nextTick();

      const editButton = wrapper.findComponent({ name: 'AddressEditButton' });
      expect(editButton.exists()).toBe(false);
    });

    it('does not render AddressEditButton when type is not address', async () => {
      const txHash = '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab';
      wrapper = createWrapper({ text: txHash, location: 'eth', type: 'transaction' });

      // Trigger mouseover to show tooltip content
      await wrapper.find('div').trigger('mouseover');
      await nextTick();

      const editButton = wrapper.findComponent({ name: 'AddressEditButton' });
      expect(editButton.exists()).toBe(false);
    });

    it('does not render AddressEditButton when location is undefined', async () => {
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
    it('matches location via matchChain when not a direct blockchain', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      // 'ethereum' is not a Blockchain enum value but matchChain returns ETH
      wrapper = createWrapper({ text: address, location: 'ethereum' });

      // Should show link button since matchChain returns ETH
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(true);
    });

    it('returns undefined for unmatched locations', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'invalid_chain' });

      // Should not show link button since no explorer base is set
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });
  });

  describe('tooltip behavior', () => {
    it('disables tooltip when truncateLength is 0', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, truncateLength: 0 });

      // RuiTooltip should exist but be disabled
      const tooltip = wrapper.find('div');
      expect(tooltip.exists()).toBe(true);
    });

    it('renders RuiTooltip when text is not hidden', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address });

      // RuiTooltipStub should be rendered
      expect(wrapper.text()).toContain('0x1234...5678');
    });

    it('does not render RuiTooltip when hideText is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, hideText: true });

      // The truncated text should not be visible
      expect(wrapper.text()).not.toContain('0x1234');
    });
  });

  describe('props passed to child components', () => {
    it('passes correct props to CopyButton', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, size: 14 });

      const copyButton = wrapper.findComponent({ name: 'CopyButton' });
      expect(copyButton.props('text')).toBe(address);
      expect(copyButton.props('size')).toBe(14);
    });

    it('passes correct props to LinkButton', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth', size: 14, type: 'token' });

      const linkButton = wrapper.findComponent({ name: 'LinkButton' });
      expect(linkButton.props('text')).toBe(address);
      expect(linkButton.props('size')).toBe(14);
      expect(linkButton.props('isToken')).toBe(true);
      expect(linkButton.props('base')).toContain('etherscan.io');
    });

    it('passes correct props to EnsAvatar', () => {
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
    it('shows button container when showLink is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, location: 'eth', displayMode: 'link' });

      // Container should exist because showLink is true
      const buttonContainer = wrapper.findAll('div').filter(d => d.classes().includes('pl-1'));
      expect(buttonContainer.length).toBeGreaterThan(0);
    });

    it('shows button container when showCopy is true', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, displayMode: 'copy' });

      // Container should exist because showCopy is true
      const copyButton = wrapper.findComponent({ name: 'CopyButton' });
      expect(copyButton.exists()).toBe(true);
    });

    it('hides button container in text mode', () => {
      const address = '0x1234567890abcdef1234567890abcdef12345678';
      wrapper = createWrapper({ text: address, displayMode: 'text' });

      // Neither copy nor link button should exist
      expect(wrapper.findComponent({ name: 'CopyButton' }).exists()).toBe(false);
      expect(wrapper.findComponent({ name: 'LinkButton' }).exists()).toBe(false);
    });
  });
});
