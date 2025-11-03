<script setup lang="ts">
interface Props {
  signingInProgress: boolean;
  primaryActionDisabled: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  'sign-in': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="space-y-4">
    <div class="text-rui-text-secondary text-sm">
      {{ t('external_services.gnosispay.siwe.sign_explanation') }}
    </div>

    <RuiButton
      :disabled="primaryActionDisabled || signingInProgress"
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
  </div>
</template>
