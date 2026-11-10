<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { ReconciliationAccount, ReconciliationBucket } from '@/modules/history/reconciliation/schemas';
import type { AccountDetailState } from '@/modules/history/reconciliation/use-bucket-reconciliation-store';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { MAX_ACCOUNT_BUCKETS } from '@/modules/history/reconciliation/api/use-bucket-reconciliation-api';
import ReconciliationAccountRow from '@/modules/history/reconciliation/components/ReconciliationAccountRow.vue';
import ReconciliationAmount from '@/modules/history/reconciliation/components/ReconciliationAmount.vue';
import ReconciliationStatusCell from '@/modules/history/reconciliation/components/ReconciliationStatusCell.vue';
import {
  accountKeyOf,
  amountsFor,
  type ReconciliationView,
  sortBuckets,
} from '@/modules/history/reconciliation/use-reconciliation-rows';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

interface BucketRow {
  kind: 'bucket';
  key: string;
  accountKey: string;
  account: ReconciliationAccount;
  bucket: ReconciliationBucket;
}

interface PlaceholderRow {
  kind: 'placeholder';
  key: string;
  accountKey: string;
  account: ReconciliationAccount;
  state: 'loading' | 'error' | 'empty';
}

interface MoreRow {
  kind: 'more';
  key: string;
  accountKey: string;
  account: ReconciliationAccount;
  shown: number;
  total: number;
}

type Row = BucketRow | PlaceholderRow | MoreRow;

const { accounts, details, view, loading = false } = defineProps<{
  accounts: ReconciliationAccount[];
  details: Record<string, AccountDetailState | undefined>;
  view: ReconciliationView;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'expand': [account: ReconciliationAccount];
  'load-more': [account: ReconciliationAccount];
  'mark-spam': [bucket: ReconciliationBucket];
  'open-issue': [issueId: number];
  'retry': [account: ReconciliationAccount];
}>();

const { t } = useI18n({ useScope: 'global' });

/** Account keys the user opened. Rows are fetched only when an account lands here. */
const expandedKeys = ref<string[]>([]);

const accountByKey = computed<Record<string, ReconciliationAccount>>(() =>
  Object.fromEntries(accounts.map(account => [accountKeyOf(account), account])));

function placeholder(account: ReconciliationAccount, state: PlaceholderRow['state']): PlaceholderRow {
  const accountKey = accountKeyOf(account);
  return {
    account,
    accountKey,
    key: `${accountKey}:placeholder`,
    kind: 'placeholder',
    state,
  };
}

function bucketRow(account: ReconciliationAccount, accountKey: string, bucket: ReconciliationBucket): BucketRow {
  return {
    account,
    accountKey,
    bucket,
    key: `${accountKey}:bucket:${bucket.protocol ?? ''}:${bucket.asset}`,
    kind: 'bucket',
  };
}

function rowsForAccount(account: ReconciliationAccount): Row[] {
  const accountKey = accountKeyOf(account);
  const detail = details[accountKey];

  if (!get(expandedKeys).includes(accountKey))
    return [placeholder(account, 'empty')];
  if (!detail || (detail.loading && detail.buckets.length === 0))
    return [placeholder(account, 'loading')];
  if (detail.error && detail.buckets.length === 0)
    return [placeholder(account, 'error')];
  if (detail.buckets.length === 0)
    return [placeholder(account, 'empty')];

  const result: Row[] = sortBuckets(detail.buckets)
    .map(bucket => bucketRow(account, accountKey, bucket));
  const { pagination } = detail;
  if (pagination.total > detail.buckets.length && detail.buckets.length < MAX_ACCOUNT_BUCKETS) {
    result.push({
      account,
      accountKey,
      key: `${accountKey}:more`,
      kind: 'more',
      shown: detail.buckets.length,
      total: pagination.total,
    });
  }
  return result;
}

const rows = computed<Row[]>(() => accounts.flatMap(rowsForAccount));

/**
 * Rows handed to the table as collapsed.
 *
 * @remarks
 * The table's grouping keeps one group per account, and hiding an account means handing it every
 * row of that group. Rows of an open account are never in this list, including rows that arrived
 * after it was opened.
 */
const collapsedRows = computed<Row[]>(() => get(rows).filter(row => !get(expandedKeys).includes(row.accountKey)));

/**
 * Applies the table's collapsed set to the open accounts.
 *
 * @remarks
 * Every account has at least a placeholder row, so an account missing from the collapsed set is
 * the one just opened. Only that opening is forwarded: re-rendering must not refetch every open
 * account.
 */
function onCollapsedUpdate(collapsed: Row[]): void {
  const collapsedKeys = new Set(collapsed.map(row => row.accountKey));
  const previouslyOpen = new Set(get(expandedKeys));
  const opened = accounts
    .map(account => accountKeyOf(account))
    .filter(key => !collapsedKeys.has(key));

  set(expandedKeys, opened);

  for (const key of opened) {
    const account = get(accountByKey)[key];
    if (!account || previouslyOpen.has(key) || details[key]?.loaded)
      continue;
    emit('expand', account);
  }
}

const cols = computed<DataTableColumn<Row>[]>(() => [
  { class: 'min-w-48', key: 'asset', label: t('common.asset') },
  { align: 'end', class: 'text-no-wrap', key: 'fromHistory', label: t('data_issues.reconciliation.table.from_history') },
  { align: 'end', class: 'text-no-wrap', key: 'onChain', label: t('data_issues.reconciliation.table.on_chain') },
  { align: 'end', class: 'text-no-wrap', key: 'difference', label: t('data_issues.reconciliation.table.difference') },
  { class: 'min-w-72 w-96', key: 'status', label: t('data_issues.reconciliation.table.status') },
]);

function amountsOf(row: BucketRow): ReturnType<typeof amountsFor> {
  return amountsFor(row.bucket);
}

const emptyDescription = computed<string>(() => (view === 'attention'
  ? t('data_issues.reconciliation.table.empty_attention')
  : t('data_issues.reconciliation.table.empty_all')));
</script>

<template>
  <RuiDataTable
    :cols="cols"
    :rows="rows"
    :loading="loading"
    group="accountKey"
    :collapsed="collapsedRows"
    row-attr="key"
    dense
    hide-pagination
    data-testid="reconciliation-table"
    @update:collapsed="onCollapsedUpdate($event ?? [])"
  >
    <template #group.header="{ header, isOpen: open, toggle: toggleGroup, colspan }">
      <ReconciliationAccountRow
        v-if="accountByKey[header.identifier]"
        :account="accountByKey[header.identifier]"
        :view="view"
        :is-open="open"
        :loading="details[header.identifier]?.loading"
        :error="details[header.identifier]?.error"
        :colspan="colspan"
        @toggle="toggleGroup()"
        @retry="emit('retry', accountByKey[header.identifier])"
      />
    </template>

    <template #item.asset="{ row }">
      <div
        v-if="row.kind === 'bucket'"
        class="flex items-center gap-2 min-w-0"
      >
        <AssetDetails :asset="row.bucket.asset" />
        <span
          v-if="row.bucket.protocol"
          class="text-rui-text-secondary flex items-center min-w-0"
        >
          <CounterpartyDisplay :counterparty="row.bucket.protocol" />
        </span>
      </div>
      <template v-else-if="row.kind === 'more'">
        <RuiButton
          size="sm"
          variant="text"
          color="primary"
          data-testid="reconciliation-load-more"
          @click="emit('load-more', row.account)"
        >
          {{ t('data_issues.reconciliation.table.load_more', { shown: row.shown, total: row.total }) }}
        </RuiButton>
      </template>
      <div
        v-else
        class="flex items-center gap-2 text-rui-text-secondary text-sm"
      >
        <RuiIcon
          v-if="row.state === 'loading'"
          name="lu-loader-circle"
          size="14"
          class="animate-spin"
        />
        <span>
          {{ row.state === 'loading'
            ? t('data_issues.reconciliation.table.loading')
            : row.state === 'error'
              ? t('data_issues.reconciliation.table.error')
              : t('data_issues.reconciliation.table.empty_placeholder') }}
        </span>
      </div>
    </template>

    <template #item.fromHistory="{ row }">
      <ReconciliationAmount
        v-if="row.kind === 'bucket'"
        :amount="amountsOf(row).derived"
        :asset="row.bucket.asset"
      />
    </template>

    <template #item.onChain="{ row }">
      <ReconciliationAmount
        v-if="row.kind === 'bucket'"
        :amount="amountsOf(row).observed"
        :asset="row.bucket.asset"
      />
    </template>

    <template #item.difference="{ row }">
      <ReconciliationAmount
        v-if="row.kind === 'bucket' && row.bucket.status === 'mismatch'"
        :amount="amountsOf(row).delta"
        :asset="row.bucket.asset"
        class="font-medium text-rui-error"
        signed
      />
      <span
        v-else
        class="text-rui-text-disabled"
      >
        {{ t('data_issues.reconciliation.no_value') }}
      </span>
    </template>

    <template #item.status="{ row }">
      <ReconciliationStatusCell
        v-if="row.kind === 'bucket'"
        :bucket="row.bucket"
        @open-issue="emit('open-issue', $event)"
        @mark-spam="emit('mark-spam', $event)"
      />
    </template>

    <template #no-data>
      <div class="py-4 text-rui-text-secondary text-sm">
        {{ emptyDescription }}
      </div>
    </template>
  </RuiDataTable>
</template>
