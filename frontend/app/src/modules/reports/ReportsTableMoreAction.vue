<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import ExportReportCsv from '@/modules/reports/ExportReportCsv.vue';
import ConfirmMenu from '@/modules/shell/components/ConfirmMenu.vue';
import { useDeleteQuestion } from '@/modules/shell/components/row-delete-question';

defineProps<{
  reportId: number;
}>();

const emit = defineEmits<{
  delete: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const toDeleteQuestion = useDeleteQuestion();

const deleteQuestion = computed<ConfirmQuestion>(() => toDeleteQuestion({
  message: t('reports_table.delete_confirm.message'),
  title: t('reports_table.delete_confirm.title'),
}));
</script>

<template>
  <ConfirmMenu
    lazy
    menu-class="max-w-60"
    :options="{ placement: 'bottom-end' }"
    close-on-content-click
  >
    <template #activator="{ attrs }">
      <RuiButton
        class="p-2!"
        icon
        variant="text"
        :aria-label="t('common.actions_text')"
        data-testid="report-more-actions"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-ellipsis-vertical"
          size="20"
        />
      </RuiButton>
    </template>
    <template #default="{ ask }">
      <div class="flex flex-col">
        <ExportReportCsv
          :report-id="reportId"
          list
        />
        <RuiButton
          variant="list"
          color="error"
          data-testid="report-delete"
          @click="ask(deleteQuestion, () => emit('delete'))"
        >
          <template #prepend>
            <RuiIcon
              size="20"
              name="lu-trash-2"
            />
          </template>

          {{ t('reports_table.delete') }}
        </RuiButton>
      </div>
    </template>
  </ConfirmMenu>
</template>
