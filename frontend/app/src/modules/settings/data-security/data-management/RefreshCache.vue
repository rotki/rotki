<script setup lang="ts">
import { assert, toCapitalCase, toSentenceCase } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import { useSessionApi } from '@/modules/session/api/use-session-api';
import { useCacheClear } from '@/modules/session/use-cache-clear';
import { useSessionPurge } from '@/modules/session/use-purge';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import ActionStatusIndicator from '@/modules/shell/components/error/ActionStatusIndicator.vue';

const source = ref<string>();

const { protocolCacheStatus } = storeToRefs(useProtocolCacheStatusStore());
const { useIsTaskRunning } = useTaskStore();

const { getChainName } = useSupportedChains();
const { refreshGeneralCache } = useSessionPurge();
const { getRefreshableGeneralCaches } = useSessionApi();
const { t } = useI18n({ useScope: 'global' });

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

const taskRunning = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
const eventTaskLoading = useIsTaskRunning(TaskType.TRANSACTIONS_DECODING);
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
    chain: getChainName(data.chain),
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
  <SettingsItem :id="SettingsHighlightIds.REFRESH_CACHE">
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
