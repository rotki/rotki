import type { useGnosisPaySigning } from '@/modules/integrations/gnosis-pay/use-gnosis-pay-signing';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { get, set } from '@vueuse/shared';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref, type VNode } from 'vue';
import GnosisPayAddressValidation from '@/modules/integrations/gnosis-pay/components/GnosisPayAddressValidation.vue';
import GnosisPayAuth from '@/modules/integrations/gnosis-pay/components/GnosisPayAuth.vue';
import GnosisPayAuthStep from '@/modules/integrations/gnosis-pay/components/GnosisPayAuthStep.vue';
import GnosisPaySignMessage from '@/modules/integrations/gnosis-pay/components/GnosisPaySignMessage.vue';
import GnosisPayWalletConnection from '@/modules/integrations/gnosis-pay/components/GnosisPayWalletConnection.vue';
import { AuthStep, GnosisPayError } from '@/modules/integrations/gnosis-pay/types';

type SigningOptions = Parameters<typeof useGnosisPaySigning>[0];

const SAFE = '0xSafe';
const ADMIN = '0xAdmin';
const STRANGER = '0xStranger';

const fetchGnosisPayAdmins = vi.fn();
const connectWallet = vi.fn();
const disconnectWallet = vi.fn();
const switchNetwork = vi.fn();
const signInWithEthereum = vi.fn();
const checkMigration = vi.fn();

const connected = ref<boolean>(false);
const connectedAddress = ref<string | undefined>();
const connectedChainId = ref<number | undefined>();
const apiKey = ref<string>('');
const cardOpen = ref<boolean>(false);

let signingOptions: SigningOptions | undefined;

vi.mock('@/modules/integrations/gnosis-pay/use-gnosis-pay-api', () => ({
  useGnosisPaySiweApi: vi.fn().mockImplementation(() => ({ fetchGnosisPayAdmins })),
}));

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: vi.fn().mockImplementation(() => ({
    connect: connectWallet,
    connected,
    connectedAddress,
    connectedChainId,
    disconnect: disconnectWallet,
    isDisconnecting: ref<boolean>(false),
    isWalletConnect: ref<boolean>(false),
    preparing: ref<boolean>(false),
    switchNetwork,
  })),
}));

vi.mock('@/modules/wallet/providers/use-unified-providers', () => ({
  useUnifiedProviders: vi.fn().mockImplementation(() => ({
    availableProviders: ref([]),
    isDetecting: ref<boolean>(false),
    showProviderSelection: ref<boolean>(false),
  })),
}));

vi.mock('@/modules/wallet/providers/use-provider-selection', () => ({
  useProviderSelection: vi.fn().mockImplementation(() => ({ handleProviderSelection: vi.fn() })),
}));

vi.mock('@/modules/integrations/gnosis-pay/use-gnosis-pay-signing', () => ({
  useGnosisPaySigning: vi.fn().mockImplementation((options: SigningOptions) => {
    signingOptions = options;
    return { signInWithEthereum };
  }),
}));

vi.mock('@/modules/integrations/gnosis-pay/use-gnosis-pay-safe-migration', () => ({
  useGnosisPaySafeMigration: vi.fn().mockImplementation(() => ({
    addFailure: ref<string | undefined>(),
    addMissingSafe: vi.fn(),
    adding: ref<boolean>(false),
    checkMigration,
    hasUntrackedSafe: ref<boolean>(false),
    safeMigrationKeypath: ref<string>(''),
    untrackedAccount: ref(),
    untrackedSafe: ref(),
  })),
}));

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: vi.fn().mockImplementation(() => ({
    deleteService: vi.fn(),
    load: vi.fn(),
    loading: ref<boolean>(false),
    useApiKey: vi.fn().mockImplementation(() => apiKey),
  })),
}));

vi.mock('@/modules/premium/use-feature-access', () => ({
  PremiumFeature: { GNOSIS_PAY: 'gnosis_pay' },
  useFeatureAccess: vi.fn().mockImplementation(() => ({
    allowed: ref<boolean>(true),
    minimumTier: ref<string | null>(null),
    premium: ref<boolean>(true),
  })),
}));

const ServiceKeyCardStub = defineComponent({
  name: 'ServiceKeyCard',
  setup(_, { expose, slots }): () => VNode {
    expose({ openDialog: cardOpen });
    return () => h('div', [slots.banner?.(), slots['left-buttons']?.(), slots.default?.()]);
  },
});

const GnosisPayAuthStepStub = defineComponent({
  name: 'GnosisPayAuthStep',
  props: {
    isClickable: { default: false, type: Boolean },
    isComplete: { default: false, type: Boolean },
    isCurrent: { default: false, type: Boolean },
    stepNumber: { required: true, type: Number },
    title: { default: '', type: String },
  },
  emits: ['click-step'],
  setup(_, { slots }): () => VNode {
    return () => h('div', slots.default?.());
  },
});

function mountAuth(): VueWrapper {
  return mount(GnosisPayAuth, {
    global: {
      stubs: {
        GnosisPayAddressValidation: true,
        GnosisPayAuthStep: GnosisPayAuthStepStub,
        GnosisPayConnected: true,
        GnosisPayNoSafe: true,
        GnosisPaySafeMigrationNotice: true,
        GnosisPaySignMessage: true,
        GnosisPayWalletConnection: true,
        ProviderSelectionDialog: true,
        RuiProgress: true,
        ServiceKeyCard: ServiceKeyCardStub,
        ServiceKeyDeleteButton: true,
      },
    },
  });
}

function options(): SigningOptions {
  if (!signingOptions)
    throw new Error('signing was not set up');
  return signingOptions;
}

function walletConnection(wrapper: VueWrapper): VueWrapper<InstanceType<typeof GnosisPayWalletConnection>> {
  return wrapper.findComponent(GnosisPayWalletConnection);
}

function addressValidation(wrapper: VueWrapper): VueWrapper<InstanceType<typeof GnosisPayAddressValidation>> {
  return wrapper.findComponent(GnosisPayAddressValidation);
}

function signMessage(wrapper: VueWrapper): VueWrapper<InstanceType<typeof GnosisPaySignMessage>> {
  return wrapper.findComponent(GnosisPaySignMessage);
}

function authStep(wrapper: VueWrapper, step: AuthStep): VueWrapper<InstanceType<typeof GnosisPayAuthStep>> {
  const found = wrapper.findAllComponents(GnosisPayAuthStep)
    .find(item => item.props('stepNumber') === step);
  if (!found)
    throw new Error(`step ${step} is not rendered`);
  return found;
}

function connectWith(address: string): void {
  set(connected, true);
  set(connectedAddress, address);
  set(connectedChainId, 100);
}

/** Opens the card's dialog, which loads the registered accounts. */
async function openDialog(): Promise<void> {
  set(cardOpen, true);
  await flushPromises();
}

/** Brings the wizard to the sign step: accounts registered, admin wallet connected and validated. */
async function mountAtSignStep(): Promise<VueWrapper> {
  connectWith(ADMIN);
  const wrapper = mountAuth();
  await openDialog();
  expect(authStep(wrapper, AuthStep.SIGN_MESSAGE).props('isCurrent')).toBe(true);
  return wrapper;
}

describe('gnosisPayAuth', () => {
  beforeEach(() => {
    signingOptions = undefined;
    fetchGnosisPayAdmins.mockReset().mockResolvedValue({ [SAFE]: [ADMIN] });
    connectWallet.mockReset().mockResolvedValue(undefined);
    disconnectWallet.mockReset().mockResolvedValue(undefined);
    switchNetwork.mockReset().mockResolvedValue(undefined);
    signInWithEthereum.mockReset();
    checkMigration.mockReset().mockResolvedValue(undefined);
    set(connected, false);
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
    set(apiKey, '');
    set(cardOpen, false);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('error messages', () => {
    const connectionCases: [GnosisPayError, { message?: string }, string][] = [
      [GnosisPayError.NO_WALLET_CONNECTED, {}, 'external_services.gnosispay.errors.no_wallet_connected'],
      [GnosisPayError.CONNECTION_FAILED, { message: 'wallet refused' }, 'wallet refused'],
      [GnosisPayError.CONNECTION_FAILED, {}, 'external_services.gnosispay.errors.connection_failed'],
      [GnosisPayError.INVALID_ADDRESS, {}, ''],
      [GnosisPayError.SIGNATURE_REJECTED, {}, ''],
      [GnosisPayError.OTHER, { message: 'boom' }, ''],
    ];

    it.each(connectionCases)('should show the connection message for %s %o', async (type, context, expected) => {
      const wrapper = mountAuth();
      options().setError(type, context);
      await flushPromises();

      expect(walletConnection(wrapper).props('connectionErrorMessage')).toBe(expected);
    });

    const validationCases: [GnosisPayError, { message?: string }, string][] = [
      [GnosisPayError.INVALID_ADDRESS, {}, 'external_services.gnosispay.errors.invalid_address'],
      [GnosisPayError.SIGNATURE_REJECTED, {}, 'external_services.gnosispay.errors.signature_rejected'],
      [GnosisPayError.OTHER, { message: 'boom' }, 'boom'],
      [GnosisPayError.OTHER, {}, 'external_services.gnosispay.errors.unknown'],
      [GnosisPayError.NO_WALLET_CONNECTED, {}, ''],
      [GnosisPayError.CONNECTION_FAILED, { message: 'wallet refused' }, ''],
    ];

    it.each(validationCases)('should show the validation message for %s %o', async (type, context, expected) => {
      const wrapper = mountAuth();
      options().setError(type, context);
      await flushPromises();

      expect(addressValidation(wrapper).props('validationErrorMessage')).toBe(expected);
    });

    it('should show neither message without an error', () => {
      const wrapper = mountAuth();

      expect(walletConnection(wrapper).props('connectionErrorMessage')).toBe('');
      expect(addressValidation(wrapper).props('validationErrorMessage')).toBe('');
    });

    it('should replace the steps with the no safe notice when no accounts are registered', async () => {
      fetchGnosisPayAdmins.mockResolvedValue({});
      const wrapper = mountAuth();
      await openDialog();

      expect(wrapper.findComponent({ name: 'GnosisPayNoSafe' }).exists()).toBe(true);
      expect(walletConnection(wrapper).exists()).toBe(false);
    });

    it('should show a failed connect as the connection message', async () => {
      connectWallet.mockRejectedValue(new Error('no provider'));
      const wrapper = mountAuth();
      walletConnection(wrapper).vm.$emit('connect-click');
      await flushPromises();

      expect(walletConnection(wrapper).props('connectionErrorMessage')).toBe('no provider');
    });
  });

  describe('step navigation', () => {
    it('should disconnect when going back to step 1', async () => {
      const wrapper = await mountAtSignStep();
      authStep(wrapper, AuthStep.CONNECT_WALLET).vm.$emit('click-step', AuthStep.CONNECT_WALLET);
      await flushPromises();

      expect(disconnectWallet).toHaveBeenCalledTimes(1);
    });

    it('should clear the validation and the error when going back to step 2', async () => {
      const wrapper = await mountAtSignStep();
      expect(addressValidation(wrapper).props('isAddressValid')).toBe(true);
      expect(addressValidation(wrapper).props('controlledSafeAddresses')).toEqual([SAFE]);
      options().setError(GnosisPayError.SIGNATURE_REJECTED);
      await flushPromises();

      authStep(wrapper, AuthStep.VALIDATE_ADDRESS).vm.$emit('click-step', AuthStep.VALIDATE_ADDRESS);
      await flushPromises();

      const validation = addressValidation(wrapper);
      expect(validation.props('isAddressValid')).toBe(false);
      expect(validation.props('controlledSafeAddresses')).toEqual([]);
      expect(validation.props('errorType')).toBeNull();
      expect(validation.props('validationErrorMessage')).toBe('');
      expect(disconnectWallet).not.toHaveBeenCalled();
    });

    it('should do nothing when asked for a step not behind the current one, before step 1 with a wallet connected', async () => {
      connectWith(ADMIN);
      const wrapper = mountAuth();
      options().setError(GnosisPayError.SIGNATURE_REJECTED);
      await flushPromises();

      authStep(wrapper, AuthStep.CONNECT_WALLET).vm.$emit('click-step', AuthStep.CONNECT_WALLET);
      authStep(wrapper, AuthStep.VALIDATE_ADDRESS).vm.$emit('click-step', AuthStep.VALIDATE_ADDRESS);
      await flushPromises();

      expect(disconnectWallet).not.toHaveBeenCalled();
      expect(addressValidation(wrapper).props('errorType')).toBe(GnosisPayError.SIGNATURE_REJECTED);
    });

    it('should not offer the sign step for navigation', async () => {
      const wrapper = await mountAtSignStep();

      expect(authStep(wrapper, AuthStep.CONNECT_WALLET).props('isClickable')).toBe(true);
      expect(authStep(wrapper, AuthStep.VALIDATE_ADDRESS).props('isClickable')).toBe(true);
      expect(authStep(wrapper, AuthStep.SIGN_MESSAGE).props('isClickable')).toBe(false);
    });
  });

  describe('primary action', () => {
    it('should be enabled with an address on gnosis chain while not signing', async () => {
      connectWith(ADMIN);
      const wrapper = mountAuth();
      await flushPromises();

      expect(signMessage(wrapper).props('primaryActionDisabled')).toBe(false);
    });

    it('should be disabled while signing', async () => {
      connectWith(ADMIN);
      const wrapper = mountAuth();
      set(options().signingInProgress, true);
      await flushPromises();

      expect(signMessage(wrapper).props('primaryActionDisabled')).toBe(true);
    });

    it('should be disabled without a connected address', async () => {
      connectWith(ADMIN);
      set(connectedAddress, undefined);
      const wrapper = mountAuth();
      await flushPromises();

      expect(signMessage(wrapper).props('primaryActionDisabled')).toBe(true);
    });

    it('should be disabled off gnosis chain', async () => {
      connectWith(ADMIN);
      set(connectedChainId, 1);
      const wrapper = mountAuth();
      await flushPromises();

      expect(signMessage(wrapper).props('primaryActionDisabled')).toBe(true);
    });

    it('should not depend on the connected flag or on validation', async () => {
      set(connectedAddress, STRANGER);
      set(connectedChainId, 100);
      const wrapper = mountAuth();
      await flushPromises();

      expect(signMessage(wrapper).props('primaryActionDisabled')).toBe(false);
    });

    it('should stop signing on cancel', async () => {
      connectWith(ADMIN);
      const wrapper = mountAuth();
      set(options().signingInProgress, true);
      signMessage(wrapper).vm.$emit('cancel');
      await flushPromises();

      expect(get(options().signingInProgress)).toBe(false);
      expect(signMessage(wrapper).props('signingInProgress')).toBe(false);
    });

    it('should switch to gnosis chain on request', async () => {
      connectWith(ADMIN);
      set(connectedChainId, 1);
      const wrapper = mountAuth();
      signMessage(wrapper).vm.$emit('switch-to-gnosis');
      await flushPromises();

      expect(switchNetwork).toHaveBeenCalledWith(100n);
    });

    it('should sign in on request', async () => {
      const wrapper = mountAuth();
      signMessage(wrapper).vm.$emit('sign-in');
      await flushPromises();

      expect(signInWithEthereum).toHaveBeenCalledTimes(1);
    });
  });

  describe('connect button', () => {
    it('should connect when no wallet is connected', async () => {
      const wrapper = mountAuth();
      walletConnection(wrapper).vm.$emit('connect-click');
      await flushPromises();

      expect(connectWallet).toHaveBeenCalledTimes(1);
      expect(disconnectWallet).not.toHaveBeenCalled();
    });

    it('should disconnect when a wallet is connected', async () => {
      connectWith(ADMIN);
      const wrapper = mountAuth();
      walletConnection(wrapper).vm.$emit('connect-click');
      await flushPromises();

      expect(disconnectWallet).toHaveBeenCalledTimes(1);
      expect(connectWallet).not.toHaveBeenCalled();
    });

    it('should connect when connected without an address', async () => {
      set(connected, true);
      const wrapper = mountAuth();
      walletConnection(wrapper).vm.$emit('connect-click');
      await flushPromises();

      expect(connectWallet).toHaveBeenCalledTimes(1);
      expect(disconnectWallet).not.toHaveBeenCalled();
    });
  });

  describe('watchers', () => {
    it('should not check the registered accounts before the dialog opens', async () => {
      mountAuth();
      await flushPromises();

      expect(fetchGnosisPayAdmins).not.toHaveBeenCalled();
    });

    it('should check the registered accounts and validate the address when the dialog opens', async () => {
      connectWith(ADMIN);
      const wrapper = mountAuth();
      await openDialog();

      expect(fetchGnosisPayAdmins).toHaveBeenCalledTimes(1);
      expect(addressValidation(wrapper).props('isAddressValid')).toBe(true);
      expect(addressValidation(wrapper).props('controlledSafeAddresses')).toEqual([SAFE]);
    });

    it('should check the accounts without validating when no wallet is connected', async () => {
      const wrapper = mountAuth();
      await openDialog();

      expect(fetchGnosisPayAdmins).toHaveBeenCalledTimes(1);
      expect(authStep(wrapper, AuthStep.CONNECT_WALLET).props('isCurrent')).toBe(true);
      expect(addressValidation(wrapper).props('validationErrorMessage')).toBe('');
    });

    it('should reset a finished sign-in when the dialog opens', async () => {
      mountAuth();
      set(options().signInSuccess, true);
      await openDialog();

      expect(get(options().signInSuccess)).toBe(false);
    });

    it('should show the session again when the dialog reopens after signing in again', async () => {
      set(apiKey, 'token');
      const wrapper = mountAuth();
      expect(wrapper.findComponent({ name: 'GnosisPayConnected' }).exists()).toBe(true);

      wrapper.findComponent({ name: 'GnosisPayConnected' }).vm.$emit('sign-in-again');
      await flushPromises();
      expect(wrapper.findComponent({ name: 'GnosisPayConnected' }).exists()).toBe(false);

      await openDialog();
      expect(wrapper.findComponent({ name: 'GnosisPayConnected' }).exists()).toBe(true);
    });

    it('should validate a newly connected address once accounts are registered', async () => {
      const wrapper = mountAuth();
      await openDialog();

      connectWith(STRANGER);
      await flushPromises();
      expect(addressValidation(wrapper).props('validationErrorMessage')).toBe('external_services.gnosispay.errors.invalid_address');

      set(connectedAddress, ADMIN);
      await flushPromises();
      expect(addressValidation(wrapper).props('isAddressValid')).toBe(true);
      expect(addressValidation(wrapper).props('controlledSafeAddresses')).toEqual([SAFE]);
    });

    it('should clear the validation when the address goes away', async () => {
      connectWith(ADMIN);
      const wrapper = mountAuth();
      await openDialog();
      expect(addressValidation(wrapper).props('isAddressValid')).toBe(true);

      set(connectedAddress, undefined);
      await flushPromises();
      expect(addressValidation(wrapper).props('isAddressValid')).toBe(false);
      expect(addressValidation(wrapper).props('controlledSafeAddresses')).toEqual([]);
    });

    it('should not validate a new address before accounts are registered', async () => {
      const wrapper = mountAuth();
      connectWith(STRANGER);
      await flushPromises();

      expect(addressValidation(wrapper).props('validationErrorMessage')).toBe('');
    });

    it('should check the safe migration only while a key is set', async () => {
      mountAuth();
      await flushPromises();
      expect(checkMigration).not.toHaveBeenCalled();

      set(apiKey, 'token');
      await flushPromises();
      expect(checkMigration).toHaveBeenCalledTimes(1);
    });
  });
});
