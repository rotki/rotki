<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const { failure, blocking = false } = defineProps<{
  /** Why listing the bank connections failed. */
  failure: unknown;
  /** Whether no connection is known, so the failure takes the page's place instead of a strip above it. */
  blocking?: boolean;
}>();

const emit = defineEmits<{
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const failureMessage = useFailureMessage();
</script>

<template>
  <div
    v-if="blocking"
    class="rounded-rui-card border border-rui-divider bg-rui-surface"
    data-testid="bank-connections-error"
  >
    <TableEmptyNotice
      icon="lu-landmark"
      :title="t('bank_balances.connections_failed')"
    >
      <TableFailureDescription
        :message="failureMessage(failure)"
        :failure="failure"
        @retry="emit('retry')"
      />
    </TableEmptyNotice>
  </div>
  <FailureStrip
    v-else
    class="mb-4"
    :title="t('bank_balances.connections_failed')"
    :failure="failure"
    data-testid="bank-connections-error"
    @retry="emit('retry')"
  />
</template>
