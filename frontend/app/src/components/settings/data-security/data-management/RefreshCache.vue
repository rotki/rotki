<script setup lang="ts">
import { RefreshableCache } from '@/types/session/purge';
import { TaskType } from '@/types/task-type';

const { t } = useI18n();

const refreshable = [
  {
    id: RefreshableCache.GENERAL_CACHE,
    text: t('data_management.refresh_cache.label.general_cache'),
    shortText: t('data_management.refresh_cache.label.general_cache_short'),
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

const { status, pending, showConfirmation } = useCacheClear<RefreshableCache>(
  refreshable,
  refreshSource,
  (source: string) => ({
    success: t('data_management.refresh_cache.success', {
      source,
    }),
    error: t('data_management.refresh_cache.error', {
      source,
    }),
  }),
  (source: string) => ({
    title: t('data_management.refresh_cache.confirm.title'),
    message: t('data_management.refresh_cache.confirm.message', {
      source,
    }),
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
    protocol: toCapitalCase(data.protocol),
    chain: get(getChainName(data.chain)),
  });
});

const loading = logicOr(pending, taskRunning, eventTaskLoading);
</script>

<template>
  <div>
    <RuiCardHeader class="p-0 mb-4">
      <template #header>
        {{ t('data_management.refresh_cache.title') }}
      </template>
      <template #subheader>
        {{ t('data_management.refresh_cache.subtitle') }}
      </template>
    </RuiCardHeader>

    <div class="flex items-center gap-4">
      <RuiAutoComplete
        v-model="source"
        class="flex-1"
        variant="outlined"
        :label="t('data_management.refresh_cache.select_cache')"
        :options="refreshable"
        text-attr="text"
        key-attr="id"
        :disabled="loading"
        :hint="hint"
      >
        <template #selection="{ item }">
          <div>{{ item.shortText || item.text }}</div>
        </template>
      </RuiAutoComplete>

      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="-mt-6"
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
      class="mt-4"
      :status="status"
    />
  </div>
</template>
