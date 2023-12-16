<script setup lang="ts">
withDefaults(
  defineProps<{
    list?: boolean;
  }>(),
  {
    list: false,
  },
);

const { createCsv } = useReportsStore();
const { setMessage } = useMessageStore();

const { t } = useI18n();
const { appSession, openDirectory } = useInterop();

const { downloadReportCSV } = useReportsApi();

function showMessage(description: string) {
  setMessage({
    title: t('profit_loss_report.csv_export_error'),
    description,
    success: false,
  });
}

async function exportCSV() {
  try {
    if (appSession) {
      const directory = await openDirectory(t('common.select_directory'));
      if (!directory)
        return;

      await createCsv(directory);
    }
    else {
      const result = await downloadReportCSV();
      if (!result.success)
        showMessage(result.message ?? t('profit_loss_report.download_failed'));
    }
  }
  catch (error: any) {
    showMessage(error.message);
  }
}

const label = computed(() => (appSession ? t('common.actions.export_csv') : t('common.actions.download_csv')));
</script>

<template>
  <RuiButton
    :variant="list ? 'list' : 'default'"
    color="primary"
    @click="exportCSV()"
  >
    <template #prepend>
      <RuiIcon
        size="20"
        name="file-download-line"
      />
    </template>
    {{ label }}
  </RuiButton>
</template>
