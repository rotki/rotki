<script setup lang="ts">
import type { BankConnection } from '@/modules/banks/types';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

/**
 * A connection's last sync, with a badge under it when the bank needs attention.
 *
 * @remarks
 * A failed sync's message sits beside its badge, cut to one line, in full on hover, so the cell is
 * never taller than the time plus one badge.
 */
const { status } = defineProps<{
  status: BankConnection['syncStatus'];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-col items-start justify-center gap-1">
    <TimeAgoDisplay
      v-if="status.lastSyncTs"
      :timestamp="status.lastSyncTs"
      class="text-rui-text-secondary"
    />
    <span
      v-else
      class="text-rui-text-secondary"
    >
      {{ t('bank_settings.sync.never') }}
    </span>
    <RuiChip
      v-if="status.authChallenge"
      color="error"
      variant="tonal"
      size="sm"
      data-testid="bank-auth-required"
    >
      {{ t('bank_settings.sync.authentication_required') }}
    </RuiChip>
    <RuiChip
      v-else-if="status.authExpired"
      color="warning"
      variant="tonal"
      size="sm"
      data-testid="bank-auth-expired"
    >
      {{ t('bank_settings.sync.authentication_expired') }}
    </RuiChip>
    <div
      v-else-if="status.lastError"
      class="flex items-center gap-2 min-w-0 max-w-full"
    >
      <RuiChip
        color="error"
        variant="tonal"
        size="sm"
        class="shrink-0"
        data-testid="bank-sync-error"
      >
        {{ t('bank_settings.sync.failed') }}
      </RuiChip>
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
        class="min-w-0"
        :class-names="{ tooltip: 'max-w-96 whitespace-normal' }"
      >
        <template #activator>
          <span
            class="block max-w-64 text-caption text-rui-text-secondary truncate"
            data-testid="bank-sync-error-message"
          >
            {{ status.lastError }}
          </span>
        </template>
        {{ status.lastError }}
      </RuiTooltip>
    </div>
  </div>
</template>
