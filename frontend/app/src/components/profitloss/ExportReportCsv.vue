<template>
  <span v-if="icon">
    <v-tooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <v-btn
          icon
          v-bind="attrs"
          small
          color="primary"
          v-on="on"
          @click="exportCSV()"
        >
          <v-icon small> mdi-export </v-icon>
        </v-btn>
      </template>
      <span>
        {{
          isPackaged
            ? t('profit_loss_report.export_csv')
            : t('profit_loss_report.download_csv')
        }}
      </span>
    </v-tooltip>
  </span>
  <v-btn
    v-else
    class="profit_loss_report__export-csv"
    depressed
    color="primary"
    @click="exportCSV()"
  >
    <v-icon small class="mr-2"> mdi-export </v-icon>
    {{
      isPackaged
        ? t('profit_loss_report.export_csv')
        : t('profit_loss_report.download_csv')
    }}
  </v-btn>
</template>

<script setup lang="ts">
import { api } from '@/services/rotkehlchen-api';
import { useMessageStore } from '@/store/message';
import { useReports } from '@/store/reports';
import { useReportsApi } from '@/services/reports';

defineProps({
  icon: {
    required: false,
    type: Boolean,
    default: false
  }
});

const { createCsv } = useReports();
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
