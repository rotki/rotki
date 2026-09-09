<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { tidyRpcConnectMessage } from '@/modules/settings/general/rpc/providers/rpc-connect-error';
import { maskRpcEndpoint } from '@/modules/settings/general/rpc/providers/rpc-providers';
import RpcProviderResultRow from '@/modules/settings/general/rpc/providers/RpcProviderResultRow.vue';
import {
  RPC_SETUP_STATUS,
  type RpcSetupRow,
  type RpcSetupSummary,
} from '@/modules/settings/general/rpc/providers/use-rpc-provider-setup';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const {
  credential = '',
  enablement = '',
  rows,
  running,
  summary,
} = defineProps<{
  /** The provider key, so a backend message quoting the endpoint does not put it on screen. */
  credential?: string;
  enablement?: string;
  rows: RpcSetupRow[];
  running: boolean;
  summary: RpcSetupSummary;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();

const failedRows = computed<RpcSetupRow[]>(() => rows.filter(row => row.status === RPC_SETUP_STATUS.FAILED));

/** Chains the run has finished with, which is what the line counts while it works. */
const settled = computed<number>(() => rows
  .filter(row => row.status !== RPC_SETUP_STATUS.PENDING && row.status !== RPC_SETUP_STATUS.RUNNING)
  .length);

const progress = computed<number>(() => rows.length === 0 ? 0 : (get(settled) / rows.length) * 100);

/**
 * The chains a stopped run never reached, so the two counts always add up to the total.
 *
 * @remarks
 * Zero on a run that walked every chain, which is what keeps the third count off the line.
 */
const untried = computed<number>(() => summary.total - summary.added - summary.failed);

/** Whether the finished run left a chain behind, the only case the counts alone under-tell. */
const hasFailures = computed<boolean>(() => !running && summary.failed > 0);

/** The chain the run is connecting to, which is the one thing the counts alone do not say. */
const runningChain = computed<string>(() =>
  rows.find(row => row.status === RPC_SETUP_STATUS.RUNNING)?.chain ?? '');

/**
 * The line the run shows while it works, with the count carried separately beside it.
 *
 * @remarks
 * Drops the chain in the gap between two chains, where no row is running and naming the one just
 * left would be a lie.
 */
const progressLabel = computed<string>(() => {
  const chain = get(runningChain);
  return chain
    ? t('rpc_provider_setup.apply.progress_chain', { chain: getChainName(chain) })
    : t('rpc_provider_setup.apply.progress');
});

/** The reason a chain was left out, in the backend's own words and with the credential hidden. */
function failureMessage(row: RpcSetupRow): string {
  if (row.status !== RPC_SETUP_STATUS.FAILED)
    return '';

  if (!row.error)
    return t('rpc_provider_setup.apply.unknown_error');

  return tidyRpcConnectMessage(credential ? maskRpcEndpoint(row.error, credential) : row.error);
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div
      class="text-sm"
      aria-live="polite"
      aria-atomic="true"
      data-testid="provider-summary"
    >
      <div
        v-if="running"
        class="flex items-center gap-2"
        data-testid="provider-progress"
      >
        <!-- Kept even between two chains, so the label does not shift when the icon goes. -->
        <div class="w-[18px] shrink-0">
          <ChainIcon
            v-if="runningChain"
            :chain="runningChain"
            size="18px"
          />
        </div>
        <span class="truncate min-w-0">{{ progressLabel }}</span>
        <span
          class="ml-auto shrink-0 text-rui-text-secondary tabular-nums"
          data-testid="provider-progress-count"
        >
          {{ t('rpc_provider_setup.apply.progress_count', { done: settled, total: rows.length }) }}
        </span>
      </div>
      <div
        v-else
        class="flex items-center flex-wrap gap-x-3 gap-y-1"
      >
        <span
          class="flex items-center gap-1"
          :class="summary.added > 0 ? 'text-rui-success' : 'text-rui-text-secondary'"
          data-testid="provider-added-count"
        >
          <RuiIcon
            name="lu-check"
            size="16"
          />
          {{ t('rpc_provider_setup.apply.count.added', { count: summary.added }) }}
        </span>
        <span
          v-if="summary.failed > 0"
          class="flex items-center gap-1 text-rui-error font-medium"
          data-testid="provider-failed-count"
        >
          <RuiIcon
            name="lu-x"
            size="16"
          />
          {{ t('rpc_provider_setup.apply.count.failed', { count: summary.failed }) }}
        </span>
        <span
          v-if="untried > 0"
          class="text-rui-text-secondary"
          data-testid="provider-untried-count"
        >
          {{ t('rpc_provider_setup.apply.count.untried', { count: untried }) }}
        </span>
        <span
          v-if="summary.archive > 0"
          class="text-rui-text-secondary"
        >
          {{ t('rpc_provider_setup.apply.summary_archive', { ...summary }) }}
        </span>
      </div>
    </div>
    <RuiProgress
      v-if="running"
      :value="progress"
      color="primary"
      size="4"
    />
    <RuiAccordions>
      <RuiAccordion
        eager
        header-grow
        :class-names="{ header: 'p-0', content: 'pt-2' }"
        data-testid="provider-details"
      >
        <template #header="{ open: expanded }">
          <span
            v-if="hasFailures && !expanded"
            class="text-xs text-rui-error font-medium"
            data-testid="provider-details-hint"
          >
            {{ t('rpc_provider_setup.apply.expand_failed', { count: summary.failed }, summary.failed) }}
          </span>
          <span
            v-else
            class="text-xs text-rui-text-secondary"
          >
            {{ t('rpc_provider_setup.apply.details') }}
          </span>
        </template>
        <div class="flex flex-col">
          <p
            v-if="!running && failedRows.length > 0 && enablement"
            class="text-xs text-rui-text-secondary pb-2"
          >
            {{ enablement }}
          </p>
          <div class="flex flex-col divide-y divide-rui-grey-100 dark:divide-rui-grey-800">
            <RpcProviderResultRow
              v-for="row in rows"
              :key="row.chain"
              :row="row"
              :message="failureMessage(row)"
            />
          </div>
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>
