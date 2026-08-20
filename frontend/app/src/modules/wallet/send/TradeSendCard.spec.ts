import type { ComponentPublicInstance, ComputedRef } from 'vue';
import type { TransactionParams } from '@/modules/wallet/types';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TradeSendCard from '@/modules/wallet/send/TradeSendCard.vue';

const RECIPIENT = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65';
const CONNECTED = '0x9531C059098e3d194fF87FebB587aB07B30B1306';
const ETHEREUM_CHAIN_ID = 1;
// A chain the backend reports but that resolves to no numeric id.
const UNRESOLVABLE_CHAIN = 'newchain';

const connected = ref<boolean>(true);
const connectedAddress = ref<string | undefined>(CONNECTED);
const connectedChainId = ref<number | undefined>(ETHEREUM_CHAIN_ID);
const isDisconnecting = ref<boolean>(false);
const isWalletConnect = ref<boolean>(false);
const preparing = ref<boolean>(false);
const supportedChainsForConnectedAccount = ref<string[]>(['ethereum']);
const waitingForWalletConfirmation = ref<boolean>(false);
const walletMode = ref<string>('local-bridge');
const switchNetwork = vi.fn();

const useQueryingBalances = ref<boolean>(false);
const warnUntrackedAddress = ref<boolean>(false);

const estimatingGas = ref<boolean>(false);
const assetBalance = ref(bigNumberify('2'));
const max = ref<string>('2');
const errorMessage = ref<string>('');
const send = vi.fn<(params: TransactionParams) => Promise<boolean>>();
const clearError = vi.fn();
const refreshAssetBalance = vi.fn();
const push = vi.fn();

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: vi.fn(() => ({
    connected,
    connectedAddress,
    connectedChainId,
    isDisconnecting,
    isWalletConnect,
    preparing,
    supportedChainsForConnectedAccount,
    switchNetwork,
    waitingForWalletConfirmation,
    walletMode,
  })),
}));

vi.mock('@/modules/wallet/use-wallet-helper', () => ({
  useWalletHelper: vi.fn(() => ({
    getChainFromChainId: (chainId: number): string => (chainId === ETHEREUM_CHAIN_ID ? 'ethereum' : 'optimism'),
    getChainIdFromChain: (chain: string): number | undefined =>
      (chain === UNRESOLVABLE_CHAIN ? undefined : ETHEREUM_CHAIN_ID),
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getNativeAsset: (): string => 'ETH' })),
}));

vi.mock('@/modules/wallet/send/use-balance-queries', () => ({
  useBalanceQueries: vi.fn(() => ({ useQueryingBalances, warnUntrackedAddress })),
}));

vi.mock('@/modules/wallet/use-tradable-asset', async () => {
  const mod = await vi.importActual<typeof import('@/modules/wallet/use-tradable-asset')>(
    '@/modules/wallet/use-tradable-asset',
  );
  const { computed } = await import('vue');
  return {
    ...mod,
    useTradableAsset: vi.fn(() => ({
      getAssetDetail: (): ComputedRef<{ symbol: string }> => computed(() => ({ symbol: 'ETH' })),
    })),
  };
});

vi.mock('@/modules/wallet/providers/use-unified-providers', () => ({
  useUnifiedProviders: vi.fn(() => ({
    availableProviders: ref([]),
    isDetecting: ref(false),
    showProviderSelection: ref(false),
  })),
}));

vi.mock('@/modules/wallet/send/use-trade-wallet-actions', () => ({
  useTradeWalletActions: vi.fn(() => ({
    clearError,
    connect: vi.fn(),
    disconnect: vi.fn(),
    errorMessage,
    selectProvider: vi.fn(),
    send,
    toggleConnection: vi.fn(),
  })),
}));

vi.mock('@/modules/wallet/send/use-trade-gas-estimation', () => ({
  useTradeGasEstimation: vi.fn(() => ({
    estimatedGasFee: ref('0'),
    estimatingGas,
    gasEstimable: ref(true),
  })),
}));

vi.mock('@/modules/wallet/send/use-trade-asset-balance', () => ({
  useTradeAssetBalance: vi.fn(() => ({
    assetBalance,
    max,
    refreshAssetBalance,
    resetMax: vi.fn(),
  })),
}));

vi.mock('@/modules/wallet/send/use-trade-recipient-warning', () => ({
  useTradeRecipientWarning: vi.fn(() => ({ showNeverInteractedWarning: ref(false) })),
}));

vi.mock('vue-router', async () => {
  const mod = await vi.importActual<typeof import('vue-router')>('vue-router');
  return { ...mod, useRouter: vi.fn(() => ({ push })) };
});

describe('tradeSendCard', () => {
  let wrapper: VueWrapper<InstanceType<typeof TradeSendCard>>;

  function createWrapper(): VueWrapper<InstanceType<typeof TradeSendCard>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(TradeSendCard, {
      global: {
        plugins: [pinia],
        stubs: {
          ProviderSelectionDialog: true,
          TradeAmountInput: true,
          TradeAssetSelector: true,
          TradeConnectedAddressBadge: true,
          TradeHistoryView: true,
          TradeRecipientAddress: true,
          WalletConnectionButton: true,
        },
      },
      provide: libraryDefaults,
    });
  }

  /** Fill the form the way the child inputs would. */
  async function enterTransfer(amount: string, recipient: string): Promise<void> {
    wrapper.findComponent({ name: 'TradeAmountInput' }).vm.$emit('update:modelValue', amount);
    wrapper.findComponent({ name: 'TradeAssetSelector' }).vm.$emit('update:modelValue', 'ETH');
    wrapper.findComponent({ name: 'TradeRecipientAddress' }).vm.$emit('update:modelValue', recipient);
    await nextTick();
  }

  beforeEach(async () => {
    vi.clearAllMocks();
    set(connected, true);
    set(connectedAddress, CONNECTED);
    set(connectedChainId, ETHEREUM_CHAIN_ID);
    set(isDisconnecting, false);
    set(isWalletConnect, false);
    set(preparing, false);
    set(supportedChainsForConnectedAccount, ['ethereum']);
    set(waitingForWalletConfirmation, false);
    set(useQueryingBalances, false);
    set(warnUntrackedAddress, false);
    set(estimatingGas, false);
    set(assetBalance, bigNumberify('2'));
    set(max, '2');
    set(errorMessage, '');
    send.mockResolvedValue(true);

    wrapper = createWrapper();
    await flushPromises();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  describe('which action the footer offers', () => {
    it('should offer to connect while no wallet is connected', async () => {
      set(connected, false);
      set(connectedAddress, undefined);
      await nextTick();

      expect(wrapper.find('[data-testid=connect-action]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=send-action]').exists()).toBe(false);
    });

    it('should offer to connect while disconnecting, even though still connected', async () => {
      set(isDisconnecting, true);
      await nextTick();

      expect(wrapper.find('[data-testid=connect-action]').exists()).toBe(true);
    });

    it('should offer to track an untracked address instead of sending', async () => {
      set(warnUntrackedAddress, true);
      await nextTick();

      expect(wrapper.find('[data-testid=track-action]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=send-action]').exists()).toBe(false);
    });

    it('should offer to switch network when the wallet is on another chain', async () => {
      set(connectedChainId, 10);
      await nextTick();

      expect(wrapper.find('[data-testid=switch-network-action]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=send-action]').exists()).toBe(false);
    });

    it('should offer to send once connected, tracked and on the right chain', () => {
      expect(wrapper.find('[data-testid=send-action]').exists()).toBe(true);
    });
  });

  describe('when the send button is usable', () => {
    it('should stay disabled until an amount and recipient are entered', async () => {
      expect(wrapper.find('[data-testid=send-action]').attributes('disabled')).toBeDefined();

      await enterTransfer('1', RECIPIENT);

      expect(wrapper.find('[data-testid=send-action]').attributes('disabled')).toBeUndefined();
    });

    it('should stay disabled for an amount over the available max', async () => {
      await enterTransfer('3', RECIPIENT);

      expect(wrapper.find('[data-testid=send-action]').attributes('disabled')).toBeDefined();
    });

    it('should stay disabled while gas is still being estimated', async () => {
      await enterTransfer('1', RECIPIENT);
      set(estimatingGas, true);
      await nextTick();

      expect(wrapper.find('[data-testid=send-action]').attributes('disabled')).toBeDefined();
    });

    it('should stay disabled while the balance is unknown', async () => {
      await enterTransfer('1', RECIPIENT);
      set(assetBalance, undefined);
      await nextTick();

      expect(wrapper.find('[data-testid=send-action]').attributes('disabled')).toBeDefined();
    });
  });

  describe('sending', () => {
    it('should send what was entered', async () => {
      await enterTransfer('1', RECIPIENT);

      await wrapper.find('[data-testid=send-action]').trigger('click');
      await flushPromises();

      expect(send).toHaveBeenCalledWith({
        amount: '1',
        assetIdentifier: 'ETH',
        chain: 'ethereum',
        native: true,
        to: RECIPIENT,
      });
    });

    it('should clear the form once the transaction is accepted', async () => {
      await enterTransfer('1', RECIPIENT);

      await wrapper.find('[data-testid=send-action]').trigger('click');
      await flushPromises();

      expect(wrapper.findComponent({ name: 'TradeAmountInput' }).props('modelValue')).toBe('');
      expect(wrapper.findComponent({ name: 'TradeRecipientAddress' }).props('modelValue')).toBe('');
    });

    it('should keep the form when the transaction is refused', async () => {
      send.mockResolvedValue(false);
      await enterTransfer('1', RECIPIENT);

      await wrapper.find('[data-testid=send-action]').trigger('click');
      await flushPromises();

      expect(wrapper.findComponent({ name: 'TradeAmountInput' }).props('modelValue')).toBe('1');
      expect(wrapper.findComponent({ name: 'TradeRecipientAddress' }).props('modelValue')).toBe(RECIPIENT);
    });
  });

  describe('what the card reports', () => {
    it('should warn that the connected address is not tracked', async () => {
      set(warnUntrackedAddress, true);
      await nextTick();

      expect(wrapper.find('[data-testid=untracked-warning]').exists()).toBe(true);
    });

    it('should not warn about tracking while disconnecting', async () => {
      set(warnUntrackedAddress, true);
      set(isDisconnecting, true);
      await nextTick();

      expect(wrapper.find('[data-testid=untracked-warning]').exists()).toBe(false);
    });

    it('should warn while balances are being queried', async () => {
      expect(wrapper.find('[data-testid=querying-balances-warning]').exists()).toBe(false);

      set(useQueryingBalances, true);
      await nextTick();

      expect(wrapper.find('[data-testid=querying-balances-warning]').exists()).toBe(true);
    });

    it('should show a wallet error and clear it on dismissal', async () => {
      set(errorMessage, 'insufficient funds');
      await nextTick();
      expect(wrapper.text()).toContain('insufficient funds');

      wrapper.findComponent<ComponentPublicInstance>('[data-testid=trade-error]').vm.$emit('close');

      expect(clearError).toHaveBeenCalledOnce();
    });

    it('should tell a wallet-connect user where to confirm', async () => {
      set(waitingForWalletConfirmation, true);
      set(isWalletConnect, true);
      await nextTick();

      expect(wrapper.text()).toContain('trade.waiting_for_confirmation.wallet_connect');
    });

    it('should tell a bridge user where to confirm', async () => {
      set(waitingForWalletConfirmation, true);
      await nextTick();

      expect(wrapper.text()).toContain('trade.waiting_for_confirmation.not_wallet_connect');
    });
  });

  describe('the other actions', () => {
    it('should route to the account form with the connected address', async () => {
      set(warnUntrackedAddress, true);
      await nextTick();

      await wrapper.find('[data-testid=track-action]').trigger('click');

      expect(push).toHaveBeenCalledWith({
        path: '/accounts/evm/accounts',
        query: { add: 'true', addressToAdd: CONNECTED },
      });
    });

    it('should ask the wallet to switch to the asset chain', async () => {
      set(connectedChainId, 10);
      await nextTick();

      await wrapper.find('[data-testid=switch-network-action]').trigger('click');

      expect(switchNetwork).toHaveBeenCalledWith(BigInt(ETHEREUM_CHAIN_ID));
    });

    it('should not ask the wallet to switch to a chain with no numeric id', async () => {
      set(supportedChainsForConnectedAccount, [UNRESOLVABLE_CHAIN]);
      set(connectedChainId, 10);
      await nextTick();

      await wrapper.find('[data-testid=switch-network-action]').trigger('click');

      // BigInt(undefined) throws, which would break the click handler entirely.
      expect(switchNetwork).not.toHaveBeenCalled();
    });

    it('should refresh the balance when the asset selector asks', async () => {
      wrapper.findComponent({ name: 'TradeAssetSelector' }).vm.$emit('refresh');
      await nextTick();

      expect(refreshAssetBalance).toHaveBeenCalledOnce();
    });
  });
});
