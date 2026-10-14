<script setup lang="ts">
import HashLink from '@/modules/shell/components/HashLink.vue';

const { safes } = defineProps<{
  /** The Gnosis Pay Safes the session covers, when known. */
  safes: string[];
}>();

const emit = defineEmits<{
  'sign-in-again': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="flex flex-col gap-3 rounded-rui-control border border-rui-divider px-4 py-3"
    data-testid="gnosis-pay-connected"
  >
    <div class="flex items-center gap-3">
      <div class="flex size-9 shrink-0 items-center justify-center rounded-full bg-rui-success/10 text-rui-success">
        <RuiIcon
          name="lu-circle-check"
          size="20"
        />
      </div>
      <div class="flex grow flex-col min-w-0">
        <span class="text-sm font-semibold text-rui-text">{{ t('external_services.status.connected') }}</span>
        <span class="text-sm text-rui-text-secondary">{{ t('external_services.gnosispay.connected.description') }}</span>
      </div>
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
        class="shrink-0"
        data-testid="gnosis-pay-sign-in-again"
        @click="emit('sign-in-again')"
      >
        {{ t('external_services.gnosispay.connected.sign_in_again') }}
      </RuiButton>
    </div>
    <div
      v-if="safes.length > 0"
      class="flex flex-col gap-1 border-t border-rui-divider pt-3"
    >
      <span class="text-sm font-medium text-rui-text-secondary">{{ t('external_services.gnosispay.connected.safes') }}</span>
      <div
        v-for="safe in safes"
        :key="safe"
        class="font-mono text-sm"
      >
        <HashLink
          :truncate-length="0"
          :text="safe"
          location="gnosis"
        />
      </div>
    </div>
  </div>
</template>
