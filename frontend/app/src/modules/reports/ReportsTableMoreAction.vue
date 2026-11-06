<script setup lang="ts">
import ExportReportCsv from '@/modules/reports/ExportReportCsv.vue';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

defineProps<{
  reportId: number;
}>();

const emit = defineEmits<{
  delete: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
/** The menu asks in place, by the row, rather than in a dialog over the page. */
const confirming = ref<boolean>(false);

function confirmDelete(): void {
  set(open, false);
  emit('delete');
}

watch(open, (isOpen) => {
  if (!isOpen)
    set(confirming, false);
});
</script>

<template>
  <RuiMenu
    v-model="open"
    lazy
    :role="confirming ? 'dialog' : undefined"
    :class-names="{ menu: confirming ? 'w-72' : 'max-w-60' }"
    :options="{ placement: 'bottom-end' }"
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
    <div
      v-if="!confirming"
      class="flex flex-col"
    >
      <ExportReportCsv
        :report-id="reportId"
        list
        @click="open = false"
      />
      <RuiButton
        variant="list"
        color="error"
        data-testid="report-delete"
        @click="confirming = true"
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
    <InlineConfirm
      v-else
      layout="panel"
      tone="error"
      :title="t('reports_table.delete_confirm.title')"
      :message="t('reports_table.delete_confirm.message')"
      :confirm-label="t('common.actions.delete')"
      @cancel="open = false"
      @confirm="confirmDelete()"
    />
  </RuiMenu>
</template>
