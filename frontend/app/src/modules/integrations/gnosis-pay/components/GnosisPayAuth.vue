<script setup lang="ts">
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import ServiceKeyCard, { type FeatureGate, type ServiceKeyAction } from '@/modules/settings/api-keys/ServiceKeyCard.vue';
import { useUnifiedProviders } from '@/modules/wallet/providers/use-unified-providers';
import ProviderSelectionDialog from '@/modules/wallet/ProviderSelectionDialog.vue';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
import { AuthStep, GnosisPayError } from '../types';
import { useGnosisPayAuthState, useGnosisPayAuthSteps } from '../use-gnosis-pay-auth-state';
import { useGnosisPaySafeMigration } from '../use-gnosis-pay-safe-migration';
import { useGnosisPaySigning } from '../use-gnosis-pay-signing';
import { useGnosisPayWallet } from '../use-gnosis-pay-wallet';
import GnosisPayAddressValidation from './GnosisPayAddressValidation.vue';
import GnosisPayAuthStep from './GnosisPayAuthStep.vue';
import GnosisPayConnected from './GnosisPayConnected.vue';
import GnosisPayNoSafe from './GnosisPayNoSafe.vue';
import GnosisPaySafeMigrationNotice from './GnosisPaySafeMigrationNotice.vue';
import GnosisPaySignMessage from './GnosisPaySignMessage.vue';
import GnosisPayWalletConnection from './GnosisPayWalletConnection.vue';

const { t } = useI18n({ useScope: 'global' });

const name = 'gnosis_pay';
const GNOSIS_CHAIN_ID = 100;
const { useApiKey, confirmDelete, load, loading } = useExternalApiKeys();
const key = useApiKey(name);

const { addMissingSafe, adding, checkMigration, hasUntrackedSafe, safeMigrationKeypath, untrackedAccount, untrackedSafe } = useGnosisPaySafeMigration();

const { allowed, minimumTier, premium } = useFeatureAccess(PremiumFeature.GNOSIS_PAY);
const featureGate = computed<FeatureGate>(() => {
  const tier = get(minimumTier);
  const message = !get(premium)
    ? t('external_services.need_premium')
    : t('external_services.need_tier', { tier });

  return { allowed: get(allowed), message };
});

const cardAction = computed<ServiceKeyAction>(() => ({
  addText: t('external_services.actions.authenticate'),
  editText: t('external_services.actions.reauthenticate'),
  hidden: true,
  statusText: t('external_services.status.connected'),
}));

const serviceKeyCard = useTemplateRef<InstanceType<typeof ServiceKeyCard>>('serviceKeyCard');

/** With a session already in place the dialog shows it; this runs the steps again on request. */
const signingInAgain = ref<boolean>(false);

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

/** The Safes the session covers: those the signing wallet controls, else every tracked one. */
const connectedSafes = computed<string[]>(() => {
  const controlled = get(controlledSafeAddresses);
  return controlled.length > 0 ? controlled : Object.keys(get(gnosisPayAdminsMapping));
});

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
  switchingNetwork,
  switchToChain,
  validateAddress,
} = wallet;

const signing = useGnosisPaySigning({
  clearError,
  connectedAddress,
  errorType,
  onSignInComplete: async () => {
    await load();
    await checkMigration();
  },
  setError,
  signingInProgress,
  signInSuccess,
});

const { signInWithEthereum } = signing;

const { currentStep, isStepComplete, isStepCurrent } = useGnosisPayAuthSteps(
  hasRegisteredAccounts,
  isWalletConnected,
  validatingAddress,
  signInSuccess,
);

const walletStore = useWalletStore();
const { connectedChainId, isDisconnecting, isWalletConnect, preparing } = storeToRefs(walletStore);

const isOnGnosisChain = computed<boolean>(() => get(connectedChainId) === GNOSIS_CHAIN_ID);

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

const primaryActionDisabled = logicOr(signingInProgress, logicNot(connectedAddress), logicNot(isOnGnosisChain));

async function switchToGnosis(): Promise<void> {
  await switchToChain(GNOSIS_CHAIN_ID);
}

function cancelSigning(): void {
  set(signingInProgress, false);
}

async function onConnectClicked(): Promise<void> {
  if (get(isWalletConnected))
    await disconnect();
  else
    await connect();
}

async function goToStep(step: number): Promise<void> {
  const current = get(currentStep);

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
  set(signingInAgain, false);
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

// Check for a Safe left untracked by the Gnosis Pay migration whenever the token changes.
watchImmediate(key, async (apiKey) => {
  if (apiKey)
    await checkMigration();
  else
    set(untrackedSafe, undefined);
});

// A completed sign-in goes back to the connected state, which names the Safe, instead of closing.
watch(() => isStepComplete(AuthStep.SIGN_MESSAGE), (complete) => {
  if (complete)
    set(signingInAgain, false);
});
</script>

<template>
  <div>
    <ServiceKeyCard
      ref="serviceKeyCard"
      :feature-gate="featureGate"
      rounded-icon
      :name="name"
      :action="cardAction"
      :key-set="!!key"
      :title="t('external_services.gnosispay.title')"
      :subtitle="t('external_services.gnosispay.description')"
      :image-src="getPublicServiceImagePath('gnosispay.png')"
    >
      <template
        v-if="key && hasUntrackedSafe"
        #banner
      >
        <GnosisPaySafeMigrationNotice
          :account="untrackedAccount"
          :keypath="safeMigrationKeypath"
          :adding="adding"
          @add="addMissingSafe()"
        />
      </template>

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

      <GnosisPayConnected
        v-if="key && !signingInAgain"
        :safes="connectedSafes"
        @sign-in-again="signingInAgain = true"
      />

      <GnosisPayNoSafe v-else-if="showNoRegisteredAccountsError" />

      <div
        v-else-if="checkingRegisteredAccounts"
        class="flex items-center gap-3 py-6 text-sm text-rui-text-secondary"
      >
        <RuiProgress
          variant="indeterminate"
          circular
          size="20"
          thickness="2"
          color="primary"
        />
        {{ t('external_services.gnosispay.siwe.checking_accounts') }}
      </div>

      <template v-else>
        <p class="m-0 mb-5 text-sm text-rui-text-secondary">
          {{ t('external_services.gnosispay.siwe.explanation') }}
        </p>
        <GnosisPayAuthStep
          :step-number="AuthStep.CONNECT_WALLET"
          :title="t('external_services.gnosispay.siwe.step1_title')"
          :is-complete="isStepComplete(AuthStep.CONNECT_WALLET)"
          :is-current="isStepCurrent(AuthStep.CONNECT_WALLET)"
          is-clickable
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

        <GnosisPayAuthStep
          :step-number="AuthStep.VALIDATE_ADDRESS"
          :title="t('external_services.gnosispay.siwe.step2_title')"
          :is-complete="isStepComplete(AuthStep.VALIDATE_ADDRESS)"
          :is-current="isStepCurrent(AuthStep.VALIDATE_ADDRESS)"
          is-clickable
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
            :is-on-gnosis-chain="isOnGnosisChain"
            :is-wallet-connected="isWalletConnected"
            :switching-network="switchingNetwork"
            :is-injected-wallet="!isWalletConnect"
            @sign-in="signInWithEthereum()"
            @cancel="cancelSigning()"
            @switch-to-gnosis="switchToGnosis()"
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
