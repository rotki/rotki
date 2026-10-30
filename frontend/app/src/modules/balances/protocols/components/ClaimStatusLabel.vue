<script setup lang="ts">
import type { ClaimStatus } from '@/modules/balances/protocols/use-claim-awaiting';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { status } = defineProps<{ status: ClaimStatus }>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <span
    v-if="status.kind === 'ready'"
    data-testid="claim-status-label"
  >
    {{ t('claims.status.ready') }}
  </span>
  <i18n-t
    v-else-if="status.kind === 'unlocks'"
    keypath="claims.status.unlocks"
    scope="global"
    tag="span"
    data-testid="claim-status-label"
  >
    <template #date>
      <DateDisplay
        :timestamp="status.availableAt"
        no-time
      />
    </template>
  </i18n-t>
  <span
    v-else
    data-testid="claim-status-label"
  >
    {{ t('claims.status.pending') }}
  </span>
</template>
