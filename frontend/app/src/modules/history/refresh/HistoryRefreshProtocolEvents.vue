<script setup lang="ts">
import { getTextToken, toHumanReadable } from '@rotki/common';
import { get, set } from '@vueuse/core';
import { isEqual } from 'es-toolkit';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useMoneriumOAuth } from '@/modules/external-services/monerium/use-monerium-auth';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';

const modelValue = defineModel<OnlineHistoryEventsQueryType[]>({ required: true });
const search = defineModel<string>('search', { required: true });

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ 'update:all-selected': [allSelected: boolean] }>();

const queries: OnlineHistoryEventsQueryType[] = [
  OnlineHistoryEventsQueryType.GNOSIS_PAY,
  OnlineHistoryEventsQueryType.MONERIUM,
];

const { t } = useI18n({ useScope: 'global' });

const { apiKey, load } = useExternalApiKeys(t);
const { authenticated: moneriumAuthenticated, refreshStatus } = useMoneriumOAuth();

interface QueryConfig {
  enabled: boolean;
  tooltip?: string;
}

const queryConfigs = computed<Record<OnlineHistoryEventsQueryType, QueryConfig>>(() => {
  const gnosisPayEnabled = !!get(apiKey('gnosis_pay'));
  const moneriumEnabled = get(moneriumAuthenticated);

  return {
    [OnlineHistoryEventsQueryType.GNOSIS_PAY]: {
      enabled: gnosisPayEnabled,
      tooltip: gnosisPayEnabled ? undefined : t('history_refresh_selection.refresh_disabled', { service: toHumanReadable(OnlineHistoryEventsQueryType.GNOSIS_PAY) }),
    },
    [OnlineHistoryEventsQueryType.MONERIUM]: {
      enabled: moneriumEnabled,
      tooltip: moneriumEnabled ? undefined : t('history_refresh_selection.refresh_disabled', { service: toHumanReadable(OnlineHistoryEventsQueryType.MONERIUM) }),
    },
  } as Record<OnlineHistoryEventsQueryType, QueryConfig>;
});

const enabledQueries = computed<OnlineHistoryEventsQueryType[]>(() =>
  queries.filter(query => get(queryConfigs)[query]?.enabled ?? true),
);

const filteredQueries = computed<OnlineHistoryEventsQueryType[]>(() => {
  const query = getTextToken(get(search));
  return queries.filter(queryType => getTextToken(queryType).includes(query));
});

function toggleSelect(query: OnlineHistoryEventsQueryType): void {
  const config = get(queryConfigs)[query];
  if (!config?.enabled)
    return;

  const current = get(modelValue);
  const isSelected = current.includes(query);
  updateSelection(isSelected ? current.filter(item => item !== query) : [...current, query]);
}

function toggleSelectAll() {
  updateSelection(get(modelValue).length > 0 ? [] : get(enabledQueries));
}

function updateSelection(selection: OnlineHistoryEventsQueryType[]): void {
  set(modelValue, selection);
  emit('update:all-selected', isEqual(selection.sort(), get(enabledQueries).sort()));
}

onBeforeMount(async () => {
  await Promise.all([
    load(),
    refreshStatus(),
  ]);
});

defineExpose({
  toggleSelectAll,
});
</script>

<template>
  <div>
    <div
      v-for="query in filteredQueries"
      :key="query"
      class="flex items-center px-4 py-1 pr-2 transition"
      :class="{
        'cursor-pointer hover:bg-rui-grey-100 hover:dark:bg-rui-grey-900': queryConfigs[query]?.enabled && !processing,
        'opacity-50 cursor-not-allowed': !queryConfigs[query]?.enabled || processing,
      }"
      @click="queryConfigs[query]?.enabled && !processing && toggleSelect(query)"
    >
      <RuiTooltip
        :disabled="!queryConfigs[query]?.tooltip"
        :popper="{ placement: 'top-start' }"
      >
        <template #activator>
          <div class="flex items-center">
            <RuiCheckbox
              :model-value="modelValue.includes(query)"
              :disabled="!queryConfigs[query]?.enabled || processing"
              color="primary"
              size="sm"
              hide-details
              @click.prevent.stop
            />

            <span class="capitalize text-sm text-rui-text-secondary">
              {{ toHumanReadable(query) }}
            </span>
          </div>
        </template>
        {{ queryConfigs[query]?.tooltip || '' }}
      </RuiTooltip>

      <div class="grow" />
    </div>
  </div>
</template>
