<script setup lang="ts">
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import ProviderSelectionDialog from '@/components/wallets/ProviderSelectionDialog.vue';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useUnifiedProviders } from '@/modules/onchain/wallet-providers/use-unified-providers';
import { useMessageStore } from '@/store/message';
import { getPublicServiceImagePath } from '@/utils/file';
import { AuthStep, GnosisPayError } from '../types';
import { useGnosisPayAuthState, useGnosisPayAuthSteps } from '../use-gnosis-pay-auth-state';
import { useGnosisPaySigning } from '../use-gnosis-pay-signing';
import { useGnosisPayWallet } from '../use-gnosis-pay-wallet';
import GnosisPayAddressValidation from './GnosisPayAddressValidation.vue';
import GnosisPayAuthStep from './GnosisPayAuthStep.vue';
import GnosisPaySignMessage from './GnosisPaySignMessage.vue';
import GnosisPayWalletConnection from './GnosisPayWalletConnection.vue';

const { t } = useI18n({ useScope: 'global' });

const name = 'gnosis_pay';
const { apiKey, confirmDelete, load, loading } = useExternalApiKeys(t);
const key = apiKey(name);

const serviceKeyCard = useTemplateRef<InstanceType<typeof ServiceKeyCard>>('serviceKeyCard');

// Message store for showing success notifications
const { setMessage } = useMessageStore();

// Initialize auth state
const authState = useGnosisPayAuthState();
const {
  checkingRegisteredAccounts,
  clearError,
  clearValidation,
  controlledSafeAddresses,
  errorCloseable,
  errorContext,
  errorType,
  gnosisPayAdminsMapping,
  hasRegisteredAccounts,
  isAddressValid,
  setError,
  showNoRegisteredAccountsError,
  signingInProgress,
  signInSuccess,
  validatingAddress,
} = authState;

// Initialize wallet connection
const wallet = useGnosisPayWallet({
  checkingRegisteredAccounts,
  clearError,
  clearValidation,
  controlledSafeAddresses,
  gnosisPayAdminsMapping,
  hasRegisteredAccounts,
  isAddressValid,
  setError,
  validatingAddress,
});

const {
  checkRegisteredAccounts,
  connect,
  connectedAddress,
  disconnect,
  handleProviderSelection,
  isWalletConnected,
  validateAddress,
} = wallet;

// Initialize signing
const signing = useGnosisPaySigning({
  clearError,
  connectedAddress,
  errorType,
  onSignInComplete: async () => {
    await load();
  },
  setError,
  signingInProgress,
  signInSuccess,
});

const { signInWithEthereum } = signing;

// Step management
const { currentStep, isStepComplete, isStepCurrent } = useGnosisPayAuthSteps(
  hasRegisteredAccounts,
  isWalletConnected,
  validatingAddress,
  signInSuccess,
);

// Wallet providers
const { isDisconnecting, preparing }
  = storeToRefs(useWalletStore());

const unifiedProviders = useUnifiedProviders();
const { availableProviders, isDetecting: detectingProviders, showProviderSelection } = unifiedProviders;

const isConnecting = logicOr(preparing, detectingProviders);

const deleteMessageConfirmation = computed<{ message: string; title: string }>(() => ({
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

const primaryActionDisabled = logicOr(signingInProgress, logicNot(connectedAddress));

async function onConnectClicked(): Promise<void> {
  if (get(isWalletConnected))
    await disconnect();
  else
    await connect();
}

async function goToStep(step: number): Promise<void> {
  const current = get(currentStep);

  // Can only go back to previous steps
  if (step >= current)
    return;

  // Navigate to the requested step by clearing state
  if (step === AuthStep.CONNECT_WALLET) {
    // Go back to Step 1: disconnect wallet
    if (get(isWalletConnected))
      await disconnect();
  }
  else if (step === AuthStep.VALIDATE_ADDRESS) {
    // Go back to Step 2: clear validation
    clearValidation();
    clearError();
  }
}

// Check for registered accounts when dialog opens
watch(() => get(serviceKeyCard)?.openDialog, async (isOpen) => {
  if (!isOpen) {
    return;
  }

  set(signInSuccess, false);
  await checkRegisteredAccounts();
  const address = get(connectedAddress);

  if (address && get(hasRegisteredAccounts))
    await validateAddress();
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
watch(() => isStepComplete(AuthStep.SIGN_MESSAGE), (complete) => {
  if (!complete) {
    return;
  }

  get(serviceKeyCard)?.setOpen(false);
  setMessage({
    description: t('external_services.gnosispay.siwe.success_message'),
    success: true,
  });
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
        <!-- Info alert -->
        <RuiAlert type="info">
          {{ t('external_services.gnosispay.siwe.explanation') }}
        </RuiAlert>

        <!-- NO_REGISTERED_ACCOUNTS error -->
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
          :is-complete="isStepComplete(AuthStep.CONNECT_WALLET)"
          :is-current="isStepCurrent(AuthStep.CONNECT_WALLET)"
          :is-clickable="true"
          @click-step="goToStep($event)"
        >
          <GnosisPayWalletConnection
            :is-wallet-connected="isWalletConnected"
            :connected-address="connectedAddress"
            :validating-address="validatingAddress"
            :is-connecting="isConnecting"
            :is-disconnecting="isDisconnecting"
            :connection-error-message="connectionErrorMessage"
            @connect-click="onConnectClicked()"
            @disconnect="disconnect()"
            @clear-error="clearError()"
          />
        </GnosisPayAuthStep>

        <!-- Step 2: Checking connected address eligibility -->
        <GnosisPayAuthStep
          :step-number="AuthStep.VALIDATE_ADDRESS"
          :title="t('external_services.gnosispay.siwe.step2_title')"
          :is-complete="isStepComplete(AuthStep.VALIDATE_ADDRESS)"
          :is-current="isStepCurrent(AuthStep.VALIDATE_ADDRESS)"
          :is-clickable="true"
          @click-step="goToStep($event)"
        >
          <GnosisPayAddressValidation
            :validating-address="validatingAddress"
            :is-address-valid="isAddressValid"
            :controlled-safe-addresses="controlledSafeAddresses"
            :validation-error-message="validationErrorMessage"
            :error-type="errorType"
            :error-context="errorContext"
            :error-closeable="errorCloseable"
            @clear-error="clearError()"
          />
        </GnosisPayAuthStep>

        <!-- Step 3: Sign Message -->
        <GnosisPayAuthStep
          :step-number="AuthStep.SIGN_MESSAGE"
          :title="t('external_services.gnosispay.siwe.step3_title')"
          :is-complete="isStepComplete(AuthStep.SIGN_MESSAGE)"
          :is-current="isStepCurrent(AuthStep.SIGN_MESSAGE)"
          :is-clickable="false"
        >
          <GnosisPaySignMessage
            :signing-in-progress="signingInProgress"
            :primary-action-disabled="primaryActionDisabled"
            @sign-in="signInWithEthereum()"
          />
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
