<script setup lang="ts">
import { addAccountLink } from '@/modules/accounts/add-account-link';

const { t } = useI18n({ useScope: 'global' });

/** The EVM accounts page's add dialog, opened on Gnosis Chain, where a Gnosis Pay Safe lives. */
const addSafeLink = addAccountLink({ addresses: [], chain: 'gnosis' });
</script>

<template>
  <div
    class="flex flex-col items-center gap-3 rounded-rui-control border border-dashed border-rui-divider px-6 py-8 text-center"
    data-testid="gnosis-pay-no-safe"
  >
    <div class="flex size-12 items-center justify-center rounded-full bg-rui-primary/10 text-rui-primary">
      <RuiIcon
        name="lu-wallet"
        size="22"
      />
    </div>
    <div class="flex flex-col gap-1 max-w-sm">
      <span class="text-base font-semibold text-rui-text">{{ t('external_services.gnosispay.no_safe.title') }}</span>
      <span class="text-sm text-rui-text-secondary">{{ t('external_services.gnosispay.no_safe.description') }}</span>
    </div>
    <RouterLink :to="addSafeLink">
      <RuiButton
        color="primary"
        data-testid="gnosis-pay-add-safe"
      >
        <template #prepend>
          <RuiIcon
            name="lu-plus"
            size="16"
          />
        </template>
        {{ t('external_services.gnosispay.no_safe.action') }}
      </RuiButton>
    </RouterLink>
  </div>
</template>
