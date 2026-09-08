<script setup lang="ts">
import type { TransactionDecodingComparison } from '@/modules/history/data-issues/schemas';
import DataIssueTransactionDiff from '@/modules/history/data-issues/components/DataIssueTransactionDiff.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { transactions, asset, timestamp } = defineProps<{
  transactions: TransactionDecodingComparison[];
  asset: string;
  timestamp?: number;
}>();

const emit = defineEmits<{
  navigate: [groupIdentifier: string];
}>();

const { t } = useI18n({ useScope: 'global' });
const show = ref<boolean>(false);

function openTransaction(groupIdentifier: string): void {
  set(show, false);
  emit('navigate', groupIdentifier);
}
</script>

<template>
  <RuiButton
    variant="text"
    color="primary"
    class="self-start mt-2"
    data-testid="data-issue-review-open"
    @click="show = true"
  >
    {{ t('data_issues.detail.comparison.review', { count: transactions.length }) }}
  </RuiButton>
  <RuiDialog
    v-model="show"
    :max-width="1100"
  >
    <RuiCard :class-names="{ content: 'overflow-y-auto max-h-[75vh]' }">
      <template #header>
        {{ t('data_issues.detail.comparison.title') }}
      </template>
      <div
        class="flex flex-col gap-4"
        data-testid="data-issue-review-content"
      >
        <p>{{ t('data_issues.detail.comparison.snapshot') }}</p>
        <div
          v-if="timestamp"
          class="text-body-2 text-rui-text-secondary"
        >
          {{ t('data_issues.detail.comparison.checked_at') }}
          <DateDisplay :timestamp="timestamp" />
        </div>
        <RuiAlert type="warning">
          {{ t('data_issues.detail.comparison.replacement_warning') }}
        </RuiAlert>
        <section
          v-for="transaction in transactions"
          :key="transaction.txHash"
          class="border border-default rounded p-4"
          data-testid="data-issue-review-transaction"
        >
          <div class="flex flex-wrap items-center justify-between gap-2 mb-4">
            <HashLink
              :text="transaction.txHash"
              :location="transaction.savedEvents[0]?.location"
              type="transaction"
              :truncate-length="12"
            />
            <RuiButton
              variant="outlined"
              color="primary"
              size="sm"
              data-testid="data-issue-review-transaction-open"
              @click="openTransaction(transaction.groupIdentifier)"
            >
              {{ t('data_issues.detail.comparison.open_transaction') }}
            </RuiButton>
          </div>
          <DataIssueTransactionDiff
            :transaction="transaction"
            :asset="asset"
          />
        </section>
      </div>
      <template #footer>
        <RuiButton
          variant="text"
          data-testid="data-issue-review-close"
          @click="show = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
