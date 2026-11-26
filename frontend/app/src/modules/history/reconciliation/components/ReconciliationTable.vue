<script setup lang="ts">
import type { InspectedBucket, ReconciliationAccount, ReconciliationBucket } from '@/modules/history/reconciliation/schemas';
import type { AccountDetailState } from '@/modules/history/reconciliation/use-bucket-reconciliation-store';
import { toHumanReadable } from '@rotki/common';
import { type DataTableColumn, RuiButton, RuiDataTable, RuiIcon, type TablePaginationData } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
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

const { accounts, autoExpand = false, details, loading = false, view } = defineProps<{
  accounts: ReconciliationAccount[];
  /** Automatically open matching accounts when a search filter narrows the table. */
  autoExpand?: boolean;
  details: Record<string, AccountDetailState | undefined>;
  view: ReconciliationView;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'expand': [account: ReconciliationAccount];
  'inspect-trace': [target: InspectedBucket];
  'load-more': [account: ReconciliationAccount];
  'mark-spam': [bucket: ReconciliationBucket];
  'open-issue': [issueId: number];
  'retry': [account: ReconciliationAccount];
}>();

/** Cap auto-expanded accounts on a broad filter so one keystroke does not fire dozens of fetches. */
const AUTO_EXPAND_LIMIT = 20;

const { t } = useI18n({ useScope: 'global' });

/** Account keys the user opened. Rows are fetched only when an account lands here. */
const expandedKeys = ref<string[]>([]);

const { getBaseCounterpartyData } = useHistoryEventCounterpartyMappings();

const expandedSet = computed<Set<string>>(() => new Set(get(expandedKeys)));
const accountByKey = computed<Record<string, ReconciliationAccount>>(() =>
  Object.fromEntries(accounts.map(account => [accountKeyOf(account), account])));

const rows = computed<Row[]>(() => accounts.flatMap(rowsForAccount));

/** Single page covering every rendered row so RuiDataTable does not clip past 10 rows. */
const wholeTable = computed<TablePaginationData>(() => ({
  limit: Math.max(get(rows).length, 1),
  page: 1,
  total: get(rows).length,
}));

/**
 * Rows handed to the table as collapsed.
 *
 * @remarks
 * The table's grouping keeps one group per account, and hiding an account means handing it every
 * row of that group. Rows of an open account are never in this list, including rows that arrived
 * after it was opened.
 */
const collapsedRows = computed<Row[]>(() =>
  get(rows).filter(row => !get(expandedSet).has(row.accountKey)));

const cols = computed<DataTableColumn<Row>[]>(() => [
  { class: 'min-w-40 w-[22%]', key: 'asset', label: t('common.asset') },
  { align: 'end', class: 'text-no-wrap w-[11%]', key: 'fromHistory', label: t('data_issues.reconciliation.table.from_history') },
  { align: 'end', class: 'text-no-wrap w-[11%]', key: 'onChain', label: t('data_issues.reconciliation.table.on_chain') },
  { align: 'end', class: 'text-no-wrap w-[10%]', key: 'difference', label: t('data_issues.reconciliation.table.difference') },
  { class: 'min-w-80 w-[46%]', key: 'status', label: t('data_issues.reconciliation.table.status') },
]);

const emptyDescription = computed<string>(() => (view === 'attention'
  ? t('data_issues.reconciliation.table.empty_attention')
  : t('data_issues.reconciliation.table.empty_all')));

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

  if (!get(expandedSet).has(accountKey))
    return [placeholder(account, 'empty')];
  if (!detail || (detail.loading && detail.buckets.length === 0))
    return [placeholder(account, 'loading')];
  if (detail.error !== undefined && detail.buckets.length === 0)
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

function syncExpandedAccounts(): void {
  const current = new Set(get(expandedKeys));
  if (!autoExpand) {
    for (const account of accounts) {
      const key = accountKeyOf(account);
      if (current.has(key) && !details[key])
        emit('expand', account);
    }
    return;
  }

  const next = [...current];
  for (const account of accounts.slice(0, AUTO_EXPAND_LIMIT)) {
    const key = accountKeyOf(account);
    if (!current.has(key))
      next.push(key);
    if (!details[key]?.loading)
      emit('expand', account);
  }
  set(expandedKeys, next);
}

/**
 * Applies the table's collapsed set to the open accounts.
 *
 * @remarks
 * Every account has at least a placeholder row, so an account missing from the collapsed set is
 * the one just opened. Only newly opened accounts are forwarded; `ensureAccount` decides via
 * `statusKey` whether cached rows can be reused.
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
    if (!account || previouslyOpen.has(key))
      continue;
    emit('expand', account);
  }
}

/** The protocol's display name, at the size of the line it sits in rather than the badge's own. */
function protocolLabel(protocol: string): string {
  return getBaseCounterpartyData(protocol)?.label ?? toHumanReadable(protocol, 'capitalize');
}

function amountsOf(row: BucketRow): ReturnType<typeof amountsFor> {
  return amountsFor(row.bucket);
}

watch(
  [() => autoExpand, () => accounts.map(accountKeyOf).join('\n')],
  () => syncExpandedAccounts(),
  { immediate: true },
);
</script>

<template>
  <RuiDataTable
    :cols="cols"
    :rows="rows"
    :loading="loading"
    group="accountKey"
    :collapsed="collapsedRows"
    :pagination="wholeTable"
    :global-items-per-page="false"
    row-attr="key"
    item-class="bg-rui-grey-50 dark:bg-white/[0.03]"
    outlined
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
        class="flex flex-col gap-1 min-w-0 py-1"
      >
        <AssetDetails :asset="row.bucket.asset" />
        <div
          v-if="row.bucket.protocol"
          class="flex items-center gap-1.5 pl-13 -mt-1 text-xs text-rui-text-secondary whitespace-nowrap"
          data-testid="reconciliation-bucket-protocol"
        >
          <CounterpartyDisplay
            :counterparty="row.bucket.protocol"
            size="14px"
            icon
          />
          <span>{{ t('data_issues.reconciliation.table.protocol_position', { protocol: protocolLabel(row.bucket.protocol) }) }}</span>
        </div>
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
        v-else-if="row.kind === 'bucket'"
        class="text-rui-text-disabled"
      >
        {{ t('data_issues.reconciliation.no_value') }}
      </span>
    </template>

    <template #item.status="{ row }">
      <ReconciliationStatusCell
        v-if="row.kind === 'bucket'"
        :bucket="row.bucket"
        :location="row.account.location"
        :location-label="row.account.locationLabel"
        @open-issue="emit('open-issue', $event)"
        @mark-spam="emit('mark-spam', $event)"
        @inspect-trace="emit('inspect-trace', { account: row.account, bucket: $event })"
      />
    </template>

    <template #no-data>
      <div class="py-4 text-rui-text-secondary text-sm">
        {{ emptyDescription }}
      </div>
    </template>
  </RuiDataTable>
</template>
