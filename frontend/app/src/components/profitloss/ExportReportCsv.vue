<script setup lang="ts">
import { api } from '@/services/rotkehlchen-api';

defineProps({
  icon: {
    required: false,
    type: Boolean,
    default: false
  }
});

const { createCsv } = useReportsStore();
const { setMessage } = useMessageStore();

const { t } = useI18n();
const { isPackaged, openDirectory } = useInterop();

const { downloadReportCSV } = useReportsApi();

const showMessage = (description: string) => {
  setMessage({
    title: t('profit_loss_report.csv_export_error').toString(),
    description,
    success: false
  });
};

const exportCSV = async () => {
  try {
    if (isPackaged && api.defaultBackend) {
      const directory = await openDirectory(
        t('profit_loss_report.select_directory').toString()
      );
      if (!directory) {
        return;
      }
      await createCsv(directory);
    } else {
      const result = await downloadReportCSV();
      if (!result.success) {
        showMessage(
          result.message ?? t('profit_loss_report.download_failed').toString()
        );
      }
    }
  } catch (e: any) {
    showMessage(e.message);
  }
};
</script>

<template>
  <span v-if="icon">
    <VTooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <RuiButton
          icon
          variant="text"
          v-bind="attrs"
          size="sm"
          color="primary"
          v-on="on"
          @click="exportCSV()"
        >
          <VIcon small> mdi-export </VIcon>
        </RuiButton>
      </template>
      <span>
        {{
          isPackaged
            ? t('profit_loss_report.export_csv')
            : t('profit_loss_report.download_csv')
        }}
      </span>
    </VTooltip>
  </span>
  <RuiButton
    v-else
    class="profit_loss_report__export-csv"
    color="primary"
    @click="exportCSV()"
  >
    <VIcon small class="mr-2"> mdi-export </VIcon>
    {{
      isPackaged
        ? t('profit_loss_report.export_csv')
        : t('profit_loss_report.download_csv')
    }}
  </RuiButton>
</template>
