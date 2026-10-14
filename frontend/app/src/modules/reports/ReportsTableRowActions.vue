<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import ReportsTableMoreAction from '@/modules/reports/ReportsTableMoreAction.vue';

const { reportId } = defineProps<{
  reportId: number;
}>();

const emit = defineEmits<{
  delete: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const reportUrl = computed<RouteLocationRaw>(() => ({
  name: '/reports/[id]',
  params: { id: reportId.toString() },
}));
</script>

<template>
  <div class="flex items-center justify-end gap-1">
    <RouterLink :to="reportUrl">
      <RuiButton
        size="sm"
        variant="text"
        color="primary"
        data-testid="report-open"
      >
        <template #prepend>
          <RuiIcon
            size="16"
            name="lu-file-text"
          />
        </template>
        {{ t('reports_table.load') }}
      </RuiButton>
    </RouterLink>

    <ReportsTableMoreAction
      :report-id="reportId"
      @delete="emit('delete')"
    />
  </div>
</template>
