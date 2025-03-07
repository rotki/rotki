<script setup lang="ts">
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import { useSessionApi } from '@/composables/api/session/index';
import { useSupportedChains } from '@/composables/info/chains';
import { useCacheClear } from '@/composables/session/cache-clear';
import { useSessionPurge } from '@/composables/session/purge';
import { useHistoryStore } from '@/store/history';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { startPromise } from '@shared/utils';

const source = ref<string>();

const { protocolCacheStatus } = storeToRefs(useHistoryStore());
const { isTaskRunning } = useTaskStore();

const { getChainName } = useSupportedChains();
const { refreshGeneralCache } = useSessionPurge();
const { getRefreshableGeneralCaches } = useSessionApi();
const { t } = useI18n();

const generalCaches = ref<string[]>([]);

const refreshable = computed(() => get(generalCaches).map(id => ({
  id,
  shortText: toSentenceCase(id),
  text: toSentenceCase(id),
})));

const { pending, showConfirmation, status } = useCacheClear<string>(
  refreshable,
  refreshGeneralCache,
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

const taskRunning = isTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
const eventTaskLoading = isTaskRunning(TaskType.TRANSACTIONS_DECODING);
const loading = logicOr(pending, taskRunning, eventTaskLoading);

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

async function getRefreshableCaches() {
  set(generalCaches, await getRefreshableGeneralCaches());
}

function confirm() {
  assert(isDefined(source));
  showConfirmation(get(source));
}

onMounted(() => {
  startPromise(getRefreshableCaches());
});
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
            @click="confirm()"
          >
            <RuiIcon name="lu-rotate-ccw" />
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
