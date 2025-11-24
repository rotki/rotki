<script setup lang="ts">
import DateTimeRangePicker from '@/components/inputs/DateTimeRangePicker.vue';

const start = defineModel<number>('start', { required: true });
const end = defineModel<number>('end', { required: true });

defineProps<{
  loading: boolean;
  refreshing: boolean;
}>();

const emit = defineEmits<{
  fetch: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-col md:flex-row gap-2 md:items-start">
    <div class="mr-4 font-semibold my-2 whitespace-nowrap">
      {{ t('wrapped.filter_by_date') }}
    </div>
    <DateTimeRangePicker
      v-model:start="start"
      v-model:end="end"
      class="flex-1"
      dense
      allow-empty
      :disabled="loading"
    />
    <RuiButton
      color="primary"
      class="h-10"
      :disabled="refreshing"
      @click="emit('fetch')"
    >
      <template #prepend>
        <RuiIcon name="lu-send-horizontal" />
      </template>
      {{ t('wrapped.get_data') }}
    </RuiButton>
  </div>
</template>
