<script setup lang="ts">
import { RuiProgress } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { computed, ref, useTemplateRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import ServiceKeyCard, { type FeatureGate, type ServiceKeyAction } from '@/modules/settings/api-keys/ServiceKeyCard.vue';
import ServiceKeyDeleteButton from '@/modules/settings/api-keys/ServiceKeyDeleteButton.vue';
import ProviderSelectionDialog from '@/modules/wallet/ProviderSelectionDialog.vue';
import { AuthStep } from '../types';
import { useGnosisPaySafeMigration } from '../use-gnosis-pay-safe-migration';
import { useGnosisPaySignIn } from '../use-gnosis-pay-sign-in';
import GnosisPayAddressValidation from './GnosisPayAddressValidation.vue';
import GnosisPayAuthStep from './GnosisPayAuthStep.vue';
import GnosisPayConnected from './GnosisPayConnected.vue';
import GnosisPayNoSafe from './GnosisPayNoSafe.vue';
import GnosisPaySafeMigrationNotice from './GnosisPaySafeMigrationNotice.vue';
import GnosisPaySignMessage from './GnosisPaySignMessage.vue';
import GnosisPayWalletConnection from './GnosisPayWalletConnection.vue';

const { t } = useI18n({ useScope: 'global' });

const name = 'gnosis_pay';
const { deleteService, load, loading, useApiKey } = useExternalApiKeys();
const key = useApiKey(name);

const { addFailure, addMissingSafe, adding, checkMigration, hasUntrackedSafe, safeMigrationKeypath, untrackedAccount, untrackedSafe } = useGnosisPaySafeMigration();

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

const {
  availableProviders,
  cancelSigning,
  checkingRegisteredAccounts,
  checkRegisteredAccounts,
  clearError,
  clearValidation,
  connectedAddress,
  connectedSafes,
  connectionErrorMessage,
  controlledSafeAddresses,
  detectingProviders,
  disconnect,
  errorCloseable,
  errorContext,
  errorType,
  goToStep,
  handleProviderSelection,
  hasRegisteredAccounts,
  isAddressValid,
  isConnecting,
  isDisconnecting,
  isOnGnosisChain,
  isStepComplete,
  isStepCurrent,
  isWalletConnect,
  isWalletConnected,
  modelShowProviderSelection: showProviderSelection,
  onConnectClicked,
  primaryActionDisabled,
  showNoRegisteredAccountsError,
  signingInProgress,
  signInSuccess,
  signInWithEthereum,
  switchingNetwork,
  switchToGnosis,
  validateAddress,
  validatingAddress,
  validationErrorMessage,
} = useGnosisPaySignIn({
  onSignInComplete: async () => {
    await load();
    await checkMigration();
  },
});

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
watch(key, async (apiKey) => {
  if (apiKey)
    await checkMigration();
  else
    set(untrackedSafe, undefined);
}, { immediate: true });

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
      :name="name"
      :action="cardAction"
      :key-set="!!key"
      :title="t('external_services.gnosispay.title')"
      :subtitle="t('external_services.gnosispay.description')"
      :image="{ rounded: true, src: getPublicServiceImagePath('gnosispay.png') }"
    >
      <template
        v-if="key && hasUntrackedSafe"
        #banner
      >
        <GnosisPaySafeMigrationNotice
          :account="untrackedAccount"
          :keypath="safeMigrationKeypath"
          :adding="adding"
          :failure="addFailure"
          @add="addMissingSafe({ inline: true })"
        />
      </template>

      <template
        v-if="key"
        #left-buttons
      >
        <ServiceKeyDeleteButton
          :disabled="loading || !key"
          :label="t('external_services.actions.remove_authentication')"
          :title="t('external_services.gnosispay.delete_confirmation.title')"
          :message="t('external_services.gnosispay.delete_confirmation.message')"
          @confirm="deleteService(name)"
        />
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
