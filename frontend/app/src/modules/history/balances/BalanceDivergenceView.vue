<script setup lang="ts">
import type { LocationLabel } from '@/modules/core/common/location';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { startPromise } from '@shared/utils';
import { hasAccountAddress } from '@/modules/accounts/account-helpers';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { type HistoricalBalanceDivergenceEvent, HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
import LocationLabelSelector from '@/modules/history/LocationLabelSelector.vue';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useHistoryStore } from '@/modules/history/use-history-store';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

interface DivergenceBoundaryEvent {
  key: 'last_matching' | 'first_diverged';
  color: 'success' | 'warning';
  event: HistoricalBalanceDivergenceEvent;
}

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getEvmChainName, isEvm, matchChain } = useSupportedChains();
const { findHistoricalBalanceDivergence } = useHistoricalBalancesApi();
const { runTask } = useTaskHandler();
const { requestNavigation, setHighlightTarget } = useHistoryEventNavigation();
const { fetchLocationLabels } = useHistoryDataFetching();
const { locationLabels } = storeToRefs(useHistoryStore());
const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

const selectedAsset = ref<string>();
const selectedChain = ref<string>();
const selectedLocationLabel = ref<string>('');
const loading = ref<boolean>(false);
const divergenceResult = ref<HistoricalBalanceDivergenceResponse>();
const divergenceError = ref<string>();

const availableLocationLabels = computed<LocationLabel[]>(() => {
  const labels = new Map<string, LocationLabel>();

  const addLabel = (item: LocationLabel): void => {
    const chain = matchChain(item.location);
    if (!chain || !isEvm(chain) || !getEvmChainName(chain))
      return;

    labels.set(`${chain}:${item.locationLabel.toLowerCase()}`, {
      location: chain,
      locationLabel: item.locationLabel,
    });
  };

  get(locationLabels).forEach(addLabel);
  Object.values(get(accountsPerChain))
    .flatMap(accounts => accounts)
    .filter(hasAccountAddress)
    .forEach(account => addLabel({
      location: account.chain,
      locationLabel: getAccountAddress(account),
    }));

  return [...labels.values()];
});

const chainOptions = computed<string[]>(() => {
  const options = new Set<string>();
  for (const item of get(availableLocationLabels)) {
    const chain = matchChain(item.location);
    if (chain)
      options.add(chain);
  }
  return [...options].sort((a, b) => a.localeCompare(b));
});

const locationLabelOptions = computed<LocationLabel[]>(() => {
  const chain = get(selectedChain);
  if (!chain)
    return [];

  return get(availableLocationLabels)
    .filter((item) => {
      const matchedChain = matchChain(item.location);
      return matchedChain === chain;
    })
    .sort((a, b) => a.locationLabel.localeCompare(b.locationLabel));
});

const selectedEvmChain = computed<string | undefined>(() => {
  const chain = get(selectedChain);
  return chain ? getEvmChainName(chain) : undefined;
});

const canFindDivergence = computed<boolean>(() =>
  !!get(selectedAsset) && !!get(selectedLocationLabel) && !!get(selectedEvmChain),
);

const divergenceEvents = computed<DivergenceBoundaryEvent[]>(() => {
  const result = get(divergenceResult);
  if (!result)
    return [];

  const events: DivergenceBoundaryEvent[] = [];
  if (result.lastMatching) {
    events.push({
      color: 'success',
      event: result.lastMatching,
      key: 'last_matching',
    });
  }
  if (result.firstDiverged) {
    events.push({
      color: 'warning',
      event: result.firstDiverged,
      key: 'first_diverged',
    });
  }
  return events;
});

const divergenceSummary = computed<string | undefined>(() => {
  const result = get(divergenceResult);
  if (!result)
    return undefined;

  if (result.status === 'no_divergence')
    return t('balance_divergence.no_divergence', { probes: result.probes.length });

  return t('balance_divergence.checked', { probes: result.probes.length });
});

function displayGroupIdentifier(groupIdentifier: string | null): string {
  return groupIdentifier ? truncateAddress(groupIdentifier, 8) : t('balance_divergence.missing_group');
}

function divergenceBoundaryLabel(key: DivergenceBoundaryEvent['key']): string {
  return key === 'last_matching'
    ? t('balance_divergence.last_matching')
    : t('balance_divergence.first_diverged');
}

function clearResult(): void {
  set(divergenceResult, undefined);
  set(divergenceError, undefined);
}

function navigateToDivergenceEvent(boundaryEvent: HistoricalBalanceDivergenceEvent): void {
  const asset = get(selectedAsset);
  if (!boundaryEvent.groupIdentifier || !asset)
    return;

  setHighlightTarget(HighlightTargetTypes.ACCOUNTING_EVENT, {
    groupIdentifier: boundaryEvent.groupIdentifier,
    identifier: boundaryEvent.eventIdentifier,
  });
  requestNavigation({
    assetFilter: asset,
    highlightedAccountingEvent: boundaryEvent.eventIdentifier,
    targetGroupIdentifier: boundaryEvent.groupIdentifier,
  });
}

async function findDivergence(): Promise<void> {
  const asset = get(selectedAsset);
  const evmChain = get(selectedEvmChain);
  const locationLabel = get(selectedLocationLabel);
  if (!asset || !evmChain || !locationLabel)
    return;

  set(loading, true);
  clearResult();
  try {
    const outcome = await runTask<HistoricalBalanceDivergenceResponse, TaskMeta>(
      async () => findHistoricalBalanceDivergence({ address: locationLabel, asset, evmChain }),
      {
        type: TaskType.QUERY_HISTORICAL_BALANCE_DIVERGENCE,
        meta: { title: t('balance_divergence.task.title', { asset }) },
        unique: false,
        guard: false,
      },
    );
    if (outcome.success) {
      set(divergenceResult, HistoricalBalanceDivergenceResponse.parse(outcome.result));
    }
    else if (!outcome.cancelled && !outcome.skipped) {
      set(divergenceError, outcome.message);
    }
  }
  catch (error: unknown) {
    set(divergenceError, getErrorMessage(error));
  }
  finally {
    set(loading, false);
  }
}

watch(chainOptions, (options) => {
  const current = get(selectedChain);
  if (!current || !options.includes(current))
    set(selectedChain, options[0]);
}, { immediate: true });

watch(locationLabelOptions, (options) => {
  const current = get(selectedLocationLabel);
  if (!current || !options.some(option => option.locationLabel === current))
    set(selectedLocationLabel, options[0]?.locationLabel ?? '');
}, { immediate: true });

watch([selectedAsset, selectedChain, selectedLocationLabel], clearResult);

onMounted(() => {
  startPromise(fetchLocationLabels());
});
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center bg-rui-primary text-white p-2 shrink-0">
      <RuiButton
        variant="text"
        size="sm"
        icon
        @click="emit('close')"
      >
        <RuiIcon
          name="lu-chevron-right"
          size="20"
        />
      </RuiButton>
      <h6 class="flex items-center text-body-1 pl-2">
        {{ t('balance_divergence.title') }}
      </h6>
      <div class="grow" />
      <RuiButton
        variant="text"
        icon
        size="sm"
        @click="emit('close')"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>

    <div class="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col gap-6">
      <div class="grid grid-cols-1 gap-4">
        <ChainSelect
          v-model="selectedChain"
          :items="chainOptions"
          evm-only
          :label="t('balance_divergence.chain')"
          data-testid="balance-divergence-chain"
        />

        <LocationLabelSelector
          v-model="selectedLocationLabel"
          :options="locationLabelOptions"
          :label="t('balance_divergence.location_label')"
          :disabled="locationLabelOptions.length === 0"
          data-testid="balance-divergence-location-label"
        />

        <AssetSelect
          v-model="selectedAsset"
          outlined
          show-ignored
          clearable
          :label="t('balance_divergence.asset')"
          :chain="selectedChain"
          data-testid="balance-divergence-asset"
        />
      </div>

      <div
        v-if="chainOptions.length === 0 || locationLabelOptions.length === 0"
        class="text-sm text-rui-text-secondary"
      >
        {{ t('balance_divergence.no_options') }}
      </div>

      <div class="flex">
        <RuiButton
          color="primary"
          :loading="loading"
          :disabled="!canFindDivergence"
          data-testid="find-divergence"
          @click="findDivergence()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-search"
              size="16"
            />
          </template>
          {{ t('balance_divergence.action') }}
        </RuiButton>
      </div>

      <div
        v-if="divergenceSummary"
        class="text-sm text-rui-text-secondary"
      >
        {{ divergenceSummary }}
      </div>

      <div
        v-if="divergenceEvents.length > 0"
        class="grid lg:grid-cols-2 gap-4"
        data-testid="divergence-boundaries"
      >
        <div
          v-for="boundary in divergenceEvents"
          :key="boundary.key"
          class="flex flex-col gap-3 rounded border border-rui-grey-300 p-4 text-sm"
          :data-testid="`divergence-${boundary.key}`"
        >
          <div class="flex items-center justify-between gap-3">
            <span
              class="font-medium"
              :class="boundary.color === 'success' ? 'text-rui-success' : 'text-rui-warning'"
            >
              {{ divergenceBoundaryLabel(boundary.key) }}
            </span>
            <RuiButton
              variant="text"
              color="primary"
              size="sm"
              :disabled="!boundary.event.groupIdentifier"
              :data-testid="`view-divergence-${boundary.key}`"
              @click="navigateToDivergenceEvent(boundary.event)"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-arrow-right"
                  size="14"
                />
              </template>
              {{ t('balance_divergence.view_event') }}
            </RuiButton>
          </div>
          <div class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 text-rui-text-secondary">
            <span>{{ t('balance_divergence.event') }}</span>
            <span class="truncate font-mono text-rui-text">
              {{ displayGroupIdentifier(boundary.event.groupIdentifier) }}
            </span>
            <span>{{ t('balance_divergence.block') }}</span>
            <span class="text-rui-text">{{ boundary.event.blockNumber }}</span>
            <span>{{ t('balance_divergence.tracked') }}</span>
            <AssetAmountDisplay
              :amount="boundary.event.trackedBalance"
              :asset="selectedAsset"
              no-collection-parent
              class="text-rui-text"
            />
            <span>{{ t('balance_divergence.onchain') }}</span>
            <AssetAmountDisplay
              :amount="boundary.event.onchainBalance"
              :asset="selectedAsset"
              no-collection-parent
              class="text-rui-text"
            />
            <span>{{ t('balance_divergence.difference') }}</span>
            <AssetAmountDisplay
              :amount="boundary.event.difference"
              :asset="selectedAsset"
              no-collection-parent
              class="text-rui-text"
            />
          </div>
        </div>
      </div>

      <div
        v-else-if="divergenceError"
        class="text-sm text-rui-error"
      >
        {{ divergenceError }}
      </div>
    </div>
  </div>
</template>
