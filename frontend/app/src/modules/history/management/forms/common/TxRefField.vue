<script setup lang="ts">
/**
 * The transaction reference of an event: an EVM hash, a Solana signature or a Bitcoin id.
 *
 * @remarks
 * When the form looks the transaction up as it is typed (EVM), it passes the lookup's state: the
 * field then shows a spinner while it runs, and a retry button once it failed.
 */
const txRef = defineModel<string>({ required: true });

const { canRetry = false, disabled = false, errorMessages, hint = '', label, loading = false } = defineProps<{
  label: string;
  errorMessages: string[];
  disabled?: boolean;
  hint?: string;
  loading?: boolean;
  canRetry?: boolean;
}>();

const emit = defineEmits<{
  blur: [];
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTextField
    v-model="txRef"
    color="primary"
    :disabled="disabled"
    data-testid="tx-ref"
    :label="label"
    required
    :hint="hint"
    :error-messages="errorMessages"
    @blur="emit('blur')"
  >
    <template
      v-if="loading || canRetry"
      #append
    >
      <RuiProgress
        v-if="loading"
        circular
        variant="indeterminate"
        color="primary"
        size="20"
        data-testid="tx-ref-loading"
      />
      <RuiTooltip
        v-else
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            icon
            variant="text"
            size="sm"
            data-testid="tx-ref-retry"
            @click="emit('retry')"
          >
            <RuiIcon name="lu-refresh-cw" />
          </RuiButton>
        </template>
        {{ t('actions.evm_tx_lookup.retry') }}
      </RuiTooltip>
    </template>
  </RuiTextField>
</template>
