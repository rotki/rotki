<script setup lang="ts">
const start = defineModel<number | undefined>('start', {
  get(value: number | undefined) {
    return value || undefined;
  },
  required: true,
  set(value: number | undefined) {
    return value || 0;
  },
});

const end = defineModel<number>('end', { required: true });

defineProps<{
  loading: boolean;
  refreshing: boolean;
  invalidRange: boolean;
}>();

const emit = defineEmits<{
  fetch: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
    <div class="flex flex-col md:flex-row md:grid-cols-4 gap-2 -mb-4 md:items-start">
      <div class="mr-4 font-semibold my-2 whitespace-nowrap">
        {{ t('wrapped.filter_by_date') }}
      </div>
      <RuiDateTimePicker
        v-model="start"
        dense
        type="epoch"
        :disabled="loading"
        class="flex-1"
        color="primary"
        variant="outlined"
        :max-date="end || undefined"
        :label="t('generate.labels.start_date')"
        allow-empty
      />
      <RuiDateTimePicker
        v-model="end"
        :min-date="start || undefined"
        dense
        :disabled="loading"
        type="epoch"
        class="flex-1"
        allow-empty
        color="primary"
        variant="outlined"
        :label="t('generate.labels.end_date')"
      />
      <RuiButton
        color="primary"
        class="h-10 mb-4"
        :disabled="refreshing"
        @click="emit('fetch')"
      >
        <template #prepend>
          <RuiIcon name="lu-send-horizontal" />
        </template>
        {{ t('wrapped.get_data') }}
      </RuiButton>
    </div>

    <RuiAlert
      v-if="invalidRange"
      type="error"
      class="mt-4"
    >
      <template #title>
        {{ t('generate.validation.end_after_start') }}
      </template>
    </RuiAlert>
  </div>
</template>
