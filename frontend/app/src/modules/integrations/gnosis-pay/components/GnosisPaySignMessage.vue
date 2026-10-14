<script setup lang="ts">
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';

interface Props {
  signingInProgress: boolean;
  primaryActionDisabled: boolean;
  isOnGnosisChain: boolean;
  isWalletConnected: boolean;
  switchingNetwork: boolean;
  /**
   * True whenever the signature is requested through an injected wallet, so the wallet has a real
   * page origin to compare the message domain against and it can never be `rotki.com`: the packaged
   * app serves the bridge page from localhost, a self-hosted deployment from its own host. Only
   * WalletConnect has no origin, and there the notice would be noise.
   */
  isInjectedWallet: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  'sign-in': [];
  'cancel': [];
  'switch-to-gnosis': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="text-sm text-rui-text-secondary">
      {{ t('external_services.gnosispay.siwe.sign_explanation') }}
    </div>

    <div
      v-if="isInjectedWallet"
      class="flex items-center gap-1 text-sm text-rui-text-secondary"
      data-testid="siwe-domain-notice"
    >
      <RuiIcon
        name="lu-info"
        size="14"
        class="shrink-0 text-rui-info"
      />
      <span class="ml-1">{{ t('external_services.gnosispay.siwe.domain_notice_short') }}</span>
      <HintMenuIcon :title="t('external_services.gnosispay.siwe.domain_notice_title')">
        {{ t('external_services.gnosispay.siwe.domain_notice') }}
      </HintMenuIcon>
    </div>

    <RuiAlert
      v-if="isWalletConnected && !isOnGnosisChain"
      type="warning"
    >
      {{ t('external_services.gnosispay.siwe.wrong_chain') }}
    </RuiAlert>

    <div class="flex gap-2 items-center">
      <RuiButton
        v-if="isWalletConnected && !isOnGnosisChain"
        :loading="switchingNetwork"
        color="primary"
        data-testid="gnosis-pay-switch-chain"
        @click="emit('switch-to-gnosis')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-repeat"
            size="16"
          />
        </template>
        {{ t('external_services.gnosispay.siwe.switch_to_gnosis') }}
      </RuiButton>

      <RuiButton
        v-else
        :disabled="primaryActionDisabled"
        :loading="signingInProgress"
        color="primary"
        data-testid="gnosis-pay-sign"
        @click="emit('sign-in')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-pencil-line"
            size="16"
          />
        </template>
        {{ t('external_services.gnosispay.siwe.sign_message') }}
      </RuiButton>

      <RuiButton
        v-if="signingInProgress"
        variant="outlined"
        color="primary"
        @click="emit('cancel')"
      >
        {{ t('common.actions.cancel') }}
      </RuiButton>
    </div>
  </div>
</template>
