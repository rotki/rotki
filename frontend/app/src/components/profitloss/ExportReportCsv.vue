<script setup lang="ts">
import { useReportsApi } from '@/composables/api/reports';
import { useInterop } from '@/composables/electron-interop';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { useMessageStore } from '@/modules/common/use-message-store';
import { useReportOperations } from '@/modules/reports/use-report-operations';

const { list = false, reportId } = defineProps<{
  list?: boolean;
  reportId: number;
}>();

const { createCsv } = useReportOperations();
const { setMessage } = useMessageStore();

const { t } = useI18n({ useScope: 'global' });
const { appSession, openDirectory } = useInterop();

const { downloadReportCSV } = useReportsApi();

function showMessage(description: string) {
  setMessage({
    description,
    success: false,
    title: t('profit_loss_report.csv_export_error'),
  });
}

async function exportCSV() {
  try {
    if (appSession) {
      const directory = await openDirectory(t('common.select_directory'));
      if (!directory)
        return;

      await createCsv(reportId, directory);
    }
    else {
      const result = await downloadReportCSV(reportId);
      if (!result.success)
        showMessage(result.message ?? t('profit_loss_report.download_failed'));
    }
  }
  catch (error: unknown) {
    showMessage(getErrorMessage(error));
  }
}

const label = computed<string>(() => (appSession ? t('common.actions.export_csv') : t('common.actions.download_csv')));
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
        name="lu-file-down"
      />
    </template>
    {{ label }}
  </RuiButton>
</template>
