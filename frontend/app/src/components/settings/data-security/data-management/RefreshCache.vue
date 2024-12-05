<script setup lang="ts">
import { RefreshableCache } from '@/types/session/purge';
import { TaskType } from '@/types/task-type';
import { useTaskStore } from '@/store/tasks';
import { useHistoryStore } from '@/store/history';
import { useCacheClear } from '@/composables/session/cache-clear';
import { useSupportedChains } from '@/composables/info/chains';
import { useSessionPurge } from '@/composables/session/purge';

const { t } = useI18n();

const refreshable = [
  {
    id: RefreshableCache.GENERAL_CACHE,
    shortText: t('data_management.refresh_cache.label.general_cache_short'),
    text: t('data_management.refresh_cache.label.general_cache'),
  },
];

const source = ref<RefreshableCache>(RefreshableCache.GENERAL_CACHE);

const { refreshGeneralCache } = useSessionPurge();
const { protocolCacheStatus } = storeToRefs(useHistoryStore());

const { isTaskRunning } = useTaskStore();
const taskRunning = isTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
const eventTaskLoading = isTaskRunning(TaskType.TRANSACTIONS_DECODING);

async function refreshSource(source: RefreshableCache) {
  if (source === RefreshableCache.GENERAL_CACHE)
    await refreshGeneralCache();
}

const { pending, showConfirmation, status } = useCacheClear<RefreshableCache>(
  refreshable,
  refreshSource,
  (source: string) => ({
    error: t('data_management.refresh_cache.error', {
      source,
    }),
    success: t('data_management.refresh_cache.success', {
      source,
    }),
  }),
  (source: string) => ({
    message: t('data_management.refresh_cache.confirm.message', {
      source,
    }),
    title: t('data_management.refresh_cache.confirm.title'),
  }),
);

const { getChainName } = useSupportedChains();

const hint = computed<string>(() => {
  if (!get(taskRunning))
    return '';

  const status = get(protocolCacheStatus);
  if (status.length === 0)
    return '';

  const data = status[0];

  return t('transactions.protocol_cache_updates.hint', {
    ...data,
    chain: get(getChainName(data.chain)),
    protocol: toCapitalCase(data.protocol),
  });
});

const loading = logicOr(pending, taskRunning, eventTaskLoading);
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('data_management.refresh_cache.title') }}
    </template>
    <template #subtitle>
      {{ t('data_management.refresh_cache.subtitle') }}
    </template>
    <div class="flex items-center gap-4">
      <RuiAutoComplete
        v-model="source"
        class="flex-1 min-w-0"
        variant="outlined"
        :label="t('data_management.refresh_cache.select_cache')"
        :options="refreshable"
        text-attr="text"
        key-attr="id"
        :disabled="loading"
        :hint="hint"
        hide-details
      >
        <template #selection="{ item }">
          <div>{{ item.shortText || item.text }}</div>
        </template>
      </RuiAutoComplete>

      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            :disabled="!source || loading"
            :loading="loading"
            @click="showConfirmation(source)"
          >
            <RuiIcon name="restart-line" />
          </RuiButton>
        </template>
        <span> {{ t('data_management.refresh_cache.tooltip') }} </span>
      </RuiTooltip>
    </div>

    <ActionStatusIndicator
      v-if="status"
      class="mt-2"
      :status="status"
    />
  </SettingsItem>
</template>
