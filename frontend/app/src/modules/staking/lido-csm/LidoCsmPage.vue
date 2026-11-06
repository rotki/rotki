<script setup lang="ts">
import type { LidoCsmNodeOperator } from '@/modules/staking/staking-types';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useLidoCsmApi } from '@/modules/staking/api/use-lido-csm-api';
import StakingLocationTitle from '@/modules/staking/components/StakingLocationTitle.vue';
import { STETH_IDENTIFIER } from '@/modules/staking/lido-csm/constants';
import LidoCsmAddDialog from '@/modules/staking/lido-csm/LidoCsmAddDialog.vue';
import LidoCsmTable from '@/modules/staking/lido-csm/LidoCsmTable.vue';
import LidoCsmTotals from '@/modules/staking/lido-csm/LidoCsmTotals.vue';

defineOptions({
  name: 'LidoCsmPage',
});

const { t } = useI18n({ useScope: 'global' });

const nodeOperators = ref<LidoCsmNodeOperator[]>([]);
const loading = ref<boolean>(false);
const dialogOpen = ref<boolean>(false);
/**
 * Why the operators or their metrics could not be loaded, above the table; the retry refreshes the
 * metrics, which also reloads the operators.
 */
const failure = shallowRef<unknown>();

const api = useLidoCsmApi();
const { fetchPrices } = usePriceTaskManager();

/** Loads the operators; the backend answers with a `message` when it listed them but missed some metrics. */
async function fetchNodeOperators(refreshMetrics = false): Promise<void> {
  set(loading, true);
  set(failure, undefined);
  try {
    const { entries, message } = refreshMetrics ? await api.refreshMetrics() : await api.listNodeOperators();
    set(nodeOperators, entries);
    if (message)
      set(failure, message);
  }
  catch (error: unknown) {
    set(failure, error);
  }
  finally {
    set(loading, false);
  }
}

async function refresh(refreshMetrics = false): Promise<void> {
  if (get(loading))
    return;

  await Promise.all([
    fetchNodeOperators(refreshMetrics),
    fetchPrices({
      ignoreCache: refreshMetrics,
      selectedAssets: [STETH_IDENTIFIER],
    }),
  ]);
}

function openAddDialog(): void {
  set(dialogOpen, true);
}

/** Reloads the list after an add, then keeps what the add could not fetch in view unless the reload failed itself. */
async function onAdded(warning?: string): Promise<void> {
  await refresh();
  if (warning && !isDefined(failure))
    set(failure, warning);
}

onMounted(async () => {
  if (get(nodeOperators).length === 0)
    await refresh();
});
</script>

<template>
  <TablePageLayout child>
    <template #title>
      <StakingLocationTitle location="lido-csm" />
    </template>
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="loading"
            @click="refresh(true)"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('staking_page.lido_csm.table.refresh_tooltip') }}
      </RuiTooltip>
      <RuiButton
        color="primary"
        :disabled="loading"
        @click="openAddDialog()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('staking_page.lido_csm.form.submit') }}
      </RuiButton>
    </template>
    <div class="flex flex-col gap-4">
      <FailureStrip
        v-if="failure"
        :title="t('staking_page.lido_csm.messages.fetch_failed')"
        :failure="failure"
        data-testid="lido-csm-failure"
        @retry="refresh(true)"
      />
      <LidoCsmTotals
        :operators="nodeOperators"
        :loading="loading"
      />

      <LidoCsmTable
        :rows="nodeOperators"
        :loading="loading"
        @add="openAddDialog()"
        @refresh="refresh()"
      />

      <LidoCsmAddDialog
        v-if="dialogOpen"
        v-model="dialogOpen"
        @added="onAdded($event)"
      />
    </div>
  </TablePageLayout>
</template>
