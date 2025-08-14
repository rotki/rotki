<script setup lang="ts">
import { getTextToken, toHumanReadable } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';

const modelValue = defineModel<OnlineHistoryEventsQueryType[]>({ required: true });
const search = defineModel<string>('search', { required: true });

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ 'update:all-selected': [allSelected: boolean] }>();

const queries: OnlineHistoryEventsQueryType[] = [
  OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
  OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
];

const filteredQueries = computed<OnlineHistoryEventsQueryType[]>(() => {
  const query = getTextToken(get(search));
  return queries.filter(queryType => getTextToken(queryType).includes(query));
});

function toggleSelect(query: OnlineHistoryEventsQueryType): void {
  if (get(modelValue).includes(query)) {
    updateSelection(get(modelValue).filter(item => item !== query));
  }
  else {
    updateSelection([...get(modelValue), query]);
  }
}

function toggleSelectAll() {
  if (get(modelValue).length > 0) {
    updateSelection([]);
  }
  else {
    updateSelection(queries);
  }
}

function updateSelection(selection: OnlineHistoryEventsQueryType[]): void {
  set(modelValue, selection);
  emit('update:all-selected', isEqual(selection.sort(), get(queries)));
}

defineExpose({
  toggleSelectAll,
});
</script>

<template>
  <div
    v-for="query in filteredQueries"
    :key="query"
    class="flex items-center px-4 py-1 pr-2 cursor-pointer hover:bg-rui-grey-100 hover:dark:bg-rui-grey-900 transition"
    @click="toggleSelect(query)"
  >
    <RuiCheckbox
      :model-value="modelValue.includes(query)"
      :disabled="processing"
      color="primary"
      size="sm"
      hide-details
      @click.prevent.stop="toggleSelect(query)"
    />

    <span class="capitalize text-sm text-rui-text-secondary">
      {{ toHumanReadable(query) }}
    </span>

    <div class="grow" />
  </div>
</template>
