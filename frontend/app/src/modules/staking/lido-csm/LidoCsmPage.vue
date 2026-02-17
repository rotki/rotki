<script setup lang="ts">
import type { LidoCsmNodeOperator } from '@/types/staking';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useLidoCsmApi } from '@/composables/api/staking/lido-csm';
import { usePriceTaskManager } from '@/modules/prices/use-price-task-manager';
import { STETH_IDENTIFIER } from '@/modules/staking/lido-csm/constants';
import LidoCsmAddDialog from '@/modules/staking/lido-csm/LidoCsmAddDialog.vue';
import LidoCsmTable from '@/modules/staking/lido-csm/LidoCsmTable.vue';
import { useMessageStore } from '@/store/message';

defineOptions({
  name: 'LidoCsmPage',
});

const { t } = useI18n({ useScope: 'global' });

const nodeOperators = ref<LidoCsmNodeOperator[]>([]);
const loading = ref<boolean>(false);
const dialogOpen = ref<boolean>(false);

const api = useLidoCsmApi();
const { setMessage } = useMessageStore();
const { fetchPrices } = usePriceTaskManager();

function notifyWarning(message?: string): void {
  if (!message)
    return;

  setMessage({
    description: message,
  });
}

async function fetchNodeOperators(refreshMetrics = false): Promise<void> {
  set(loading, true);
  try {
    const { entries, message } = refreshMetrics ? await api.refreshMetrics() : await api.listNodeOperators();
    set(nodeOperators, entries);
    notifyWarning(message);
  }
  catch (error: unknown) {
    setMessage({
      description: t('staking_page.lido_csm.messages.fetch_failed', { message: error instanceof Error ? error.message : String(error) }),
    });
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

onMounted(async () => {
  if (get(nodeOperators).length === 0)
    await refresh();
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking_page.lido_csm.title')]"
    child
  >
    <template #buttons>
      <RuiButton
        color="primary"
        :disabled="loading"
        @click="openAddDialog()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-plus"
            size="18"
          />
        </template>
        {{ t('staking_page.lido_csm.form.submit') }}
      </RuiButton>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="loading"
            @click="refresh(true)"
          >
            <template #prepend>
              <RuiIcon
                name="lu-refresh-ccw"
                size="20"
              />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('staking_page.lido_csm.table.refresh_tooltip') }}
      </RuiTooltip>
    </template>
    <div class="flex flex-col gap-6">
      <p class="text-sm text-rui-text-secondary">
        {{ t('staking_page.lido_csm.description') }}
      </p>

      <LidoCsmTable
        :rows="nodeOperators"
        :loading="loading"
        @refresh="refresh()"
      />

      <LidoCsmAddDialog
        v-if="dialogOpen"
        v-model="dialogOpen"
        @refresh="refresh()"
      />
    </div>
  </TablePageLayout>
</template>
