<script setup lang="ts">
import type { BrowserProvider } from 'ethers';
import type { EnhancedProviderDetail } from '@/modules/onchain/wallet-providers/provider-detection';
import type { TaskMeta } from '@/types/task';
import { gnosis } from '@reown/appkit/networks';
import GnosisPayAuthStep from '@/components/settings/api-keys/external/GnosisPayAuthStep.vue';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import ProviderSelectionDialog from '@/components/wallets/ProviderSelectionDialog.vue';
import WalletConnectionButton from '@/components/wallets/WalletConnectionButton.vue';
import { useGnosisPaySiweApi } from '@/composables/api/settings/gnosis-pay-siwe';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useInjectedWallet } from '@/modules/onchain/wallet-bridge/use-injected-wallet';
import { useWalletConnect } from '@/modules/onchain/wallet-connect/use-wallet-connect';
import { isUserRejectedError, WALLET_MODES } from '@/modules/onchain/wallet-constants';
import { useProviderSelection } from '@/modules/onchain/wallet-providers/use-provider-selection';
import { useUnifiedProviders } from '@/modules/onchain/wallet-providers/use-unified-providers';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { getPublicServiceImagePath } from '@/utils/file';
import { logger } from '@/utils/logging';

enum GnosisPayError {
  NO_REGISTERED_ACCOUNTS = 'NO_REGISTERED_ACCOUNTS',
  NO_WALLET_CONNECTED = 'NO_WALLET_CONNECTED',
  INVALID_ADDRESS = 'INVALID_ADDRESS',
  SIGNATURE_REJECTED = 'SIGNATURE_REJECTED',
  CONNECTION_FAILED = 'CONNECTION_FAILED',
  OTHER = 'OTHER',
}

enum AuthStep {
  NOT_READY = 0,
  CONNECT_WALLET = 1,
  VALIDATE_ADDRESS = 2,
  SIGN_MESSAGE = 3,
  COMPLETE = 4,
}

const { t } = useI18n({ useScope: 'global' });

const errorType = ref<GnosisPayError | null>(null);
const errorContext = ref<{ adminsMapping?: Record<string, string[]>; message?: string }>({});
const signingInProgress = ref<boolean>(false);
const validatingAddress = ref<boolean>(false);
const isAddressValid = ref<boolean>(false);
const gnosisPayAdminsMapping = ref<Record<string, string[]>>({});
const controlledSafeAddresses = ref<string[]>([]);
const checkingRegisteredAccounts = ref<boolean>(false);
const hasRegisteredAccounts = ref<boolean>(false);
const signInSuccess = ref<boolean>(false);

const name = 'gnosis_pay';
const { apiKey, confirmDelete, load, loading } = useExternalApiKeys(t);

const key = apiKey(name);

const serviceKeyCard = useTemplateRef<InstanceType<typeof ServiceKeyCard>>('serviceKeyCard');

// Message store for showing success notifications
const { setMessage } = useMessageStore();

// Task store for async task management
const { awaitTask } = useTaskStore();

// Gnosis Pay SIWE API
const { fetchGnosisPayAdmins, fetchNonce, verifySiweSignature } = useGnosisPaySiweApi();

// Wallet connection
const walletStore = useWalletStore();
const {
  connected,
  connectedAddress,
  connectedChainId,
  isDisconnecting,
  isWalletConnect,
  preparing,
  waitingForWalletConfirmation,
  walletMode,
} = storeToRefs(walletStore);

const { connect: connectWallet, disconnect: disconnectWallet, switchNetwork } = walletStore;

const isWalletConnected = computed<boolean>(() => get(connected) && !!get(connectedAddress));
const isOnGnosisChain = computed<boolean>(() => get(connectedChainId) === gnosis.id);
const switchingNetwork = ref<boolean>(false);

const errorCloseable = computed<boolean>(() => {
  const type = get(errorType);
  if (!type)
    return true;

  // Non-closeable errors:
  // 1. No registered accounts
  // 2. Connected wallet address is not valid
  return type !== GnosisPayError.NO_REGISTERED_ACCOUNTS
    && type !== GnosisPayError.INVALID_ADDRESS;
});

const currentStep = computed<number>(() => {
  // Skip showing the account verification step - it happens in background
  if (!get(hasRegisteredAccounts))
    return AuthStep.NOT_READY;
  if (!get(isWalletConnected))
    return AuthStep.CONNECT_WALLET;
  if (get(validatingAddress))
    return AuthStep.VALIDATE_ADDRESS;
  if (!get(signInSuccess))
    return AuthStep.SIGN_MESSAGE;
  return AuthStep.COMPLETE;
});

const showNoRegisteredAccountsError = computed<boolean>(() => get(errorType) === GnosisPayError.NO_REGISTERED_ACCOUNTS);

// Step state helpers
function isStepComplete(step: number): boolean {
  return get(currentStep) > step;
}

function isStepCurrent(step: number): boolean {
  return get(currentStep) === step;
}

const isStep1Complete = computed<boolean>(() => isStepComplete(AuthStep.CONNECT_WALLET));
const isStep1Current = computed<boolean>(() => isStepCurrent(AuthStep.CONNECT_WALLET));
const isStep2Complete = computed<boolean>(() => isStepComplete(AuthStep.VALIDATE_ADDRESS));
const isStep2Current = computed<boolean>(() => isStepCurrent(AuthStep.VALIDATE_ADDRESS));
const isStep3Complete = computed<boolean>(() => isStepComplete(AuthStep.SIGN_MESSAGE));
const isStep3Current = computed<boolean>(() => isStepCurrent(AuthStep.SIGN_MESSAGE));

const deleteMessageConfirmation = computed(() => ({
  message: t('external_services.gnosispay.delete_confirmation.message'),
  title: t('external_services.gnosispay.delete_confirmation.title'),
}));

// Separate error messages for different steps
const connectionErrorMessage = computed<string>(() => {
  const type = get(errorType);
  if (!type)
    return '';

  const context = get(errorContext);

  switch (type) {
    case GnosisPayError.NO_WALLET_CONNECTED:
      return t('external_services.gnosispay.errors.no_wallet_connected');
    case GnosisPayError.CONNECTION_FAILED:
      return context.message || t('external_services.gnosispay.errors.connection_failed');
    default:
      return '';
  }
});

const validationErrorMessage = computed<string>(() => {
  const type = get(errorType);
  if (!type)
    return '';

  const context = get(errorContext);

  switch (type) {
    case GnosisPayError.INVALID_ADDRESS:
      return t('external_services.gnosispay.errors.invalid_address');
    case GnosisPayError.SIGNATURE_REJECTED:
      return t('external_services.gnosispay.errors.signature_rejected');
    case GnosisPayError.OTHER:
      return context.message || t('external_services.gnosispay.errors.unknown');
    default:
      return '';
  }
});

const primaryActionDisabled = logicOr(signingInProgress, logicNot(connectedAddress), logicNot(isOnGnosisChain));

const injectedWallet = useInjectedWallet();
const walletConnect = useWalletConnect();
const unifiedProviders = useUnifiedProviders();
const { availableProviders, isDetecting: detectingProviders, showProviderSelection } = unifiedProviders;

const isConnecting = logicOr(preparing, detectingProviders);

const { handleProviderSelection: handleProviderSelectionBase } = useProviderSelection();

function clearError(): void {
  set(errorType, null);
  set(errorContext, {});
}

function clearValidation(): void {
  set(isAddressValid, false);
  set(controlledSafeAddresses, []);
}

async function checkRegisteredAccounts(): Promise<void> {
  try {
    clearError();
    set(checkingRegisteredAccounts, true);
    set(hasRegisteredAccounts, false);

    const admins = await fetchGnosisPayAdmins();

    // Check if there are any registered Gnosis Pay safe accounts
    if (Object.keys(admins).length === 0) {
      set(errorType, GnosisPayError.NO_REGISTERED_ACCOUNTS);
      return;
    }

    set(hasRegisteredAccounts, true);
    set(gnosisPayAdminsMapping, admins);
  }
  catch (error: any) {
    set(hasRegisteredAccounts, false);
    logger.error('Failed to check registered accounts:', error);
    set(errorType, GnosisPayError.OTHER);
    set(errorContext, { message: error.message || error.toString() });
  }
  finally {
    set(checkingRegisteredAccounts, false);
  }
}

async function handleProviderSelection(provider: EnhancedProviderDetail): Promise<void> {
  await handleProviderSelectionBase(provider, (message) => {
    set(errorType, GnosisPayError.CONNECTION_FAILED);
    set(errorContext, { message });
  });
}

async function validateAddress(): Promise<void> {
  try {
    clearError();
    set(validatingAddress, true);
    clearValidation();

    const address = get(connectedAddress);
    if (!address) {
      set(errorType, GnosisPayError.NO_WALLET_CONNECTED);
      return;
    }

    const adminsMapping = get(gnosisPayAdminsMapping);
    const addressLower = address.toLowerCase();

    // Find all safe addresses this admin address controls
    const foundSafeAddresses = Object.entries(adminsMapping)
      .filter(([, adminAddresses]) =>
        adminAddresses.some(adminAddr => adminAddr.toLowerCase() === addressLower))
      .map(([safeAddress]) => safeAddress);

    if (foundSafeAddresses.length === 0) {
      set(errorType, GnosisPayError.INVALID_ADDRESS);
      set(errorContext, { adminsMapping });
      return;
    }

    set(isAddressValid, true);
    set(controlledSafeAddresses, foundSafeAddresses);
  }
  catch (error: any) {
    clearValidation();
    logger.error('Address validation failed:', error);
    set(errorType, GnosisPayError.OTHER);
    set(errorContext, { message: error.message || error.toString() });
  }
  finally {
    set(validatingAddress, false);
  }
}

async function connect(): Promise<void> {
  try {
    clearError();
    clearValidation();
    await connectWallet();
    // Address validation will be triggered by the watcher when connectedAddress changes
  }
  catch (error: any) {
    logger.error(error);
    set(errorType, GnosisPayError.CONNECTION_FAILED);
    set(errorContext, { message: error.message });
  }
}

async function disconnect(): Promise<void> {
  try {
    clearError();
    clearValidation();
    await disconnectWallet();
  }
  catch (error: any) {
    logger.error(error);
    set(errorType, GnosisPayError.CONNECTION_FAILED);
    set(errorContext, { message: error.message });
  }
}

async function switchToGnosis(): Promise<void> {
  try {
    set(switchingNetwork, true);
    await switchNetwork(BigInt(gnosis.id));
  }
  catch (error: any) {
    logger.error('Failed to switch to Gnosis network:', error);
    set(errorType, GnosisPayError.CONNECTION_FAILED);
    set(errorContext, { message: error.message });
  }
  finally {
    set(switchingNetwork, false);
  }
}

function cancelSigning(): void {
  set(signingInProgress, false);
}

async function onConnectClicked(): Promise<void> {
  if (get(isWalletConnected)) {
    await disconnect();
  }
  else {
    await connect();
  }
}

async function goToStep(step: number): Promise<void> {
  const current = get(currentStep);

  // Can only go back to previous steps
  if (step >= current)
    return;

  // Navigate to the requested step by clearing state
  if (step === AuthStep.CONNECT_WALLET) {
    // Go back to Step 1: disconnect wallet
    if (get(isWalletConnected)) {
      await disconnect();
    }
  }
  else if (step === AuthStep.VALIDATE_ADDRESS) {
    // Go back to Step 2: clear validation
    clearValidation();
    clearError();
  }
}

function createSiweMessage(address: string, nonce: string): string {
  const domain = 'https://rotki.com';
  const issuedAt = new Date().toISOString();

  return `${domain} wants you to sign in with your Ethereum account:
${address}

Sign in with Ethereum to authenticate with Gnosis Pay.

URI: ${domain}
Version: 1
Chain ID: 100
Nonce: ${nonce}
Issued At: ${issuedAt}`;
}

async function signMessage(provider: BrowserProvider, message: string): Promise<string> {
  const signer = await provider.getSigner();
  return await signer.signMessage(message);
}

function getBrowserProvider(): BrowserProvider {
  if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
    return injectedWallet.getBrowserProvider();
  }
  return walletConnect.getBrowserProvider();
}

async function signInWithEthereum(): Promise<void> {
  try {
    // Preserve INVALID_ADDRESS warning during sign-in
    if (get(errorType) !== GnosisPayError.INVALID_ADDRESS) {
      clearError();
    }
    set(signingInProgress, true);
    set(signInSuccess, false);

    const address = get(connectedAddress);
    if (!address) {
      set(errorType, GnosisPayError.NO_WALLET_CONNECTED);
      return;
    }

    // Fetch nonce with async task
    const nonceTask = await fetchNonce();
    const { result: nonce } = await awaitTask<string, TaskMeta>(
      nonceTask.taskId,
      TaskType.GNOSISPAY_FETCH_NONCE,
      {
        title: t('external_services.gnosispay.siwe.fetching_nonce'),
      },
    );

    const message = createSiweMessage(address, nonce);
    const provider = getBrowserProvider();
    const signature = await signMessage(provider, message);

    // Verify signature with async task
    const verifyTask = await verifySiweSignature(message, signature);
    const { result } = await awaitTask<boolean, TaskMeta>(
      verifyTask.taskId,
      TaskType.GNOSISPAY_VERIFY_SIGNATURE,
      {
        title: t('external_services.gnosispay.siwe.verifying_signature'),
      },
    );

    if (result) {
      await load();
      set(signInSuccess, true);
    }
    else {
      throw new Error(t('external_services.gnosispay.siwe.failed'));
    }
  }
  catch (error: any) {
    if (!isTaskCancelled(error)) {
      if (isUserRejectedError(error)) {
        set(errorType, GnosisPayError.SIGNATURE_REJECTED);
      }
      else {
        setMessage({
          description: error.toString(),
          success: false,
          title: t('external_services.gnosispay.siwe.failed'),
        });
      }
      logger.error('Sign-in with Ethereum failed:', error);
    }
  }
  finally {
    set(signingInProgress, false);
  }
}

// Check for registered accounts when dialog opens
watch(() => get(serviceKeyCard)?.openDialog, async (isOpen) => {
  if (isOpen) {
    set(signInSuccess, false);
    await checkRegisteredAccounts();
    // If wallet is already connected, validate the address
    const address = get(connectedAddress);
    if (address && get(hasRegisteredAccounts)) {
      await validateAddress();
    }
  }
});

// Validate address when it changes (e.g., when user is already connected)
watch(connectedAddress, async (address) => {
  if (address && get(hasRegisteredAccounts)) {
    await validateAddress();
  }
  else {
    clearValidation();
  }
});

// When authentication is complete, close dialog and show success message
watch(isStep3Complete, (complete) => {
  if (complete) {
    get(serviceKeyCard)?.setOpen(false);
    setMessage({
      description: t('external_services.gnosispay.siwe.success_message'),
      success: true,
    });
  }
});
</script>

<template>
  <div>
    <ServiceKeyCard
      ref="serviceKeyCard"
      need-premium
      rounded-icon
      :name="name"
      :add-button-text="t('external_services.actions.authenticate')"
      :edit-button-text="t('external_services.actions.reauthenticate')"
      :key-set="!!key"
      :title="t('external_services.gnosispay.title')"
      :subtitle="t('external_services.gnosispay.description')"
      :image-src="getPublicServiceImagePath('gnosispay.png')"
      hide-action
    >
      <template
        v-if="key"
        #left-buttons
      >
        <RuiButton
          :disabled="loading || !key"
          color="error"
          variant="text"
          @click="confirmDelete(name, undefined, deleteMessageConfirmation)"
        >
          <template #prepend>
            <RuiIcon
              name="lu-trash-2"
              size="16"
            />
          </template>
          {{ t('external_services.actions.remove_authentication') }}
        </RuiButton>
      </template>

      <!-- Top Alerts -->
      <div class="mb-6 space-y-4">
        <!-- NO_REGISTERED_ACCOUNTS error -->
        <RuiAlert
          type="info"
        >
          {{ t('external_services.gnosispay.siwe.explanation') }}
        </RuiAlert>
        <RuiAlert
          v-if="showNoRegisteredAccountsError"
          type="error"
        >
          {{ t('external_services.gnosispay.errors.no_registered_accounts') }}
        </RuiAlert>

        <!-- Info/Loading alert -->
        <RuiAlert
          v-if="checkingRegisteredAccounts"
          type="info"
        >
          {{ t('external_services.gnosispay.siwe.checking_accounts') }}
        </RuiAlert>
      </div>

      <template v-if="!showNoRegisteredAccountsError && !checkingRegisteredAccounts">
        <!-- Step 1: Select Wallet Mode & Connect -->
        <GnosisPayAuthStep
          :step-number="AuthStep.CONNECT_WALLET"
          :title="t('external_services.gnosispay.siwe.step1_title')"
          :is-complete="isStep1Complete"
          :is-current="isStep1Current"
          :is-clickable="true"
          @click-step="goToStep($event)"
        >
          <!-- Wallet mode selection (only show if not connected) -->
          <div v-if="!isWalletConnected">
            <div class="text-rui-text-secondary text-caption uppercase mb-2">
              {{ t('trade.wallet_mode.label') }}
            </div>
            <RuiButtonGroup
              v-model="walletMode"
              variant="outlined"
              color="primary"
              :required="true"
              size="sm"
            >
              <RuiButton :model-value="WALLET_MODES.LOCAL_BRIDGE">
                {{ t('trade.wallet_mode.local_bridge') }}
              </RuiButton>
              <RuiButton :model-value="WALLET_MODES.WALLET_CONNECT">
                {{ t('trade.wallet_mode.wallet_connect') }}
              </RuiButton>
            </RuiButtonGroup>
          </div>

          <!-- Waiting for wallet confirmation -->
          <RuiAlert
            v-if="waitingForWalletConfirmation"
            type="info"
          >
            {{
              isWalletConnect
                ? t('trade.waiting_for_confirmation.wallet_connect')
                : t('trade.waiting_for_confirmation.not_wallet_connect')
            }}
          </RuiAlert>

          <!-- Connect button -->
          <WalletConnectionButton
            v-if="!isWalletConnected || isDisconnecting"
            :connected="isWalletConnected"
            :loading="isConnecting || isDisconnecting || validatingAddress"
            @click="onConnectClicked()"
          />

          <!-- Connection errors -->
          <RuiAlert
            v-if="connectionErrorMessage"
            type="error"
            variant="default"
            :closeable="true"
            @close="clearError()"
          >
            <div class="whitespace-pre-line">
              {{ connectionErrorMessage }}
            </div>
          </RuiAlert>

          <!-- Connected address display -->
          <div
            v-if="isWalletConnected"
            class="flex flex-col items-start"
          >
            <div class="text-caption text-rui-text-secondary mb-2">
              {{ t('external_services.gnosispay.siwe.connected_address') }}
            </div>
            <div
              class="border border-default rounded-md px-3 py-1 flex items-center gap-2 font-mono text-sm font-medium mb-3"
            >
              <div class="p-0.5 rounded-full size-3 border border-rui-success-lighter/40">
                <div class="size-full rounded-full bg-rui-success-lighter" />
              </div>
              <HashLink
                :truncate-length="0"
                :text="connectedAddress!"
                location="gnosis"
              />
            </div>
            <RuiButton
              color="primary"
              variant="outlined"
              @click="disconnect()"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-unplug"
                  size="16"
                />
              </template>
              {{ t('external_services.gnosispay.siwe.disconnect') }}
            </RuiButton>
          </div>
        </GnosisPayAuthStep>

        <!-- Step 2: Checking connected address eligibility -->
        <GnosisPayAuthStep
          :step-number="AuthStep.VALIDATE_ADDRESS"
          :title="t('external_services.gnosispay.siwe.step2_title')"
          :is-complete="isStep2Complete"
          :is-current="isStep2Current"
          :is-clickable="true"
          @click-step="goToStep($event)"
        >
          <!-- Validating address -->
          <RuiAlert
            v-if="validatingAddress"
            type="info"
          >
            {{ t('external_services.gnosispay.siwe.validating_address') }}
          </RuiAlert>

          <!-- Address validation success -->
          <RuiAlert
            v-else-if="isAddressValid"
            type="success"
          >
            <div>{{ t('external_services.gnosispay.siwe.controlled_safe') }}</div>
            <div class="mt-2 font-mono text-caption">
              <div
                v-for="safeAddress in controlledSafeAddresses"
                :key="safeAddress"
              >
                <HashLink
                  :truncate-length="0"
                  :text="safeAddress"
                  location="gnosis"
                />
              </div>
            </div>
          </RuiAlert>

          <!-- Validation errors -->
          <RuiAlert
            v-if="validationErrorMessage"
            :type="errorType === GnosisPayError.INVALID_ADDRESS ? 'warning' : 'error'"
            variant="default"
            :closeable="errorCloseable"
            @close="clearError()"
          >
            <div class="whitespace-pre-line">
              {{ validationErrorMessage }}
            </div>
          </RuiAlert>

          <!-- Invalid address - show allowed admin addresses -->
          <div v-if="errorType === GnosisPayError.INVALID_ADDRESS">
            <div class="text-caption text-rui-text-secondary mb-2">
              {{ t('external_services.gnosispay.errors.allowed_admin_addresses') }}
            </div>
            <template v-if="errorContext?.adminsMapping">
              <div
                v-for="[safeAddress, adminAddresses] in Object.entries(errorContext.adminsMapping)"
                :key="safeAddress"
                class="mb-3"
              >
                <div class="mb-1 text-rui-text-secondary flex gap-2 items-center">
                  <div class="text-[10px] uppercase">
                    {{ t('external_services.gnosispay.errors.safe_wallet') }}
                  </div>
                  <HashLink
                    :truncate-length="0"
                    :text="safeAddress"
                    location="gnosis"
                  />
                </div>
                <div class="relative ml-[5.25rem]">
                  <div class="absolute border-l border-default flex h-[calc(100%-0.75rem)]" />
                  <div
                    v-for="adminAddress in adminAddresses"
                    :key="adminAddress"
                    class="font-medium flex items-center gap-2"
                  >
                    <div class="border-t w-2 border-default" />
                    <HashLink
                      :truncate-length="0"
                      :text="adminAddress"
                      location="gnosis"
                    />
                  </div>
                </div>
              </div>
            </template>
          </div>
        </GnosisPayAuthStep>

        <!-- Step 3: Sign Message -->
        <GnosisPayAuthStep
          :step-number="AuthStep.SIGN_MESSAGE"
          :title="t('external_services.gnosispay.siwe.step3_title')"
          :is-complete="isStep3Complete"
          :is-current="isStep3Current"
          :is-clickable="false"
        >
          <div class="text-rui-text-secondary text-sm">
            {{ t('external_services.gnosispay.siwe.sign_explanation') }}
          </div>

          <!-- Warning when not on Gnosis chain -->
          <RuiAlert
            v-if="isWalletConnected && !isOnGnosisChain"
            type="warning"
          >
            {{ t('external_services.gnosispay.siwe.wrong_chain') }}
          </RuiAlert>

          <div class="flex gap-2 items-center">
            <!-- Switch to Gnosis button when not on correct chain -->
            <RuiButton
              v-if="isWalletConnected && !isOnGnosisChain"
              :loading="switchingNetwork"
              color="primary"
              @click="switchToGnosis()"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-repeat"
                  size="16"
                />
              </template>
              {{ t('external_services.gnosispay.siwe.switch_to_gnosis') }}
            </RuiButton>

            <!-- Sign button -->
            <RuiButton
              v-else
              :disabled="primaryActionDisabled"
              :loading="signingInProgress"
              color="primary"
              @click="signInWithEthereum()"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-pencil-line"
                  size="16"
                />
              </template>
              {{ t('external_services.gnosispay.siwe.sign_message') }}
            </RuiButton>

            <!-- Cancel button when signing is in progress -->
            <RuiButton
              v-if="signingInProgress"
              variant="outlined"
              color="primary"
              @click="cancelSigning()"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>
          </div>
        </GnosisPayAuthStep>
      </template>
    </ServiceKeyCard>

    <ProviderSelectionDialog
      v-model="showProviderSelection"
      :providers="availableProviders"
      :loading="detectingProviders"
      @select-provider="handleProviderSelection($event)"
    />
  </div>
</template>
