<script setup lang="ts">
import type { HistoryEventEntryType } from '@rotki/common';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { canPickEntryType, entryTypeOptions } from '@/modules/history/management/forms/entry-type-options';

const entryType = defineModel<HistoryEventEntryType>({ required: true });

const { data } = defineProps<{ data: GroupEventData | StandaloneEventData }>();

const { t } = useI18n({ useScope: 'global' });

const options = computed<HistoryEventEntryType[]>(() => entryTypeOptions(data));
const locked = computed<boolean>(() => !canPickEntryType(data));
</script>

<template>
  <RuiMenuSelect
    v-model="entryType"
    data-testid="entry-type"
    :options="options"
    :disabled="locked"
    :label="t('common.entry_type')"
    details="hidden"
  >
    <template #selection="{ item }">
      <span class="capitalize">
        {{ item }}
      </span>
    </template>
    <template #item="{ item }">
      <span class="capitalize">
        {{ item }}
      </span>
    </template>
  </RuiMenuSelect>
</template>
