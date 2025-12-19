<script setup lang="ts">
interface Props {
  signingInProgress: boolean;
  primaryActionDisabled: boolean;
  isOnGnosisChain: boolean;
  isWalletConnected: boolean;
  switchingNetwork: boolean;
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
  <div class="space-y-4">
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

      <!-- Sign button -->
      <RuiButton
        v-else
        :disabled="primaryActionDisabled"
        :loading="signingInProgress"
        color="primary"
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

      <!-- Cancel button when signing is in progress -->
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
