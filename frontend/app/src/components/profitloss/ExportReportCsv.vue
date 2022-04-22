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
          packaged
            ? $t('profit_loss_report.export_csv')
            : $t('profit_loss_report.download_csv')
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
    {{
      packaged
        ? $t('profit_loss_report.export_csv')
        : $t('profit_loss_report.download_csv')
    }}
  </v-btn>
</template>

<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';
import { useInterop } from '@/electron-interop';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useReports } from '@/store/reports';
import { useMainStore } from '@/store/store';

export default defineComponent({
  name: 'ExportReportCsv',
  props: {
    icon: {
      required: false,
      type: Boolean,
      default: false
    }
  },
  setup() {
    const { createCsv } = useReports();
    const { setMessage } = useMainStore();

    const showMessage = (description: string) => {
      setMessage({
        title: i18n.t('profit_loss_report.csv_export_error').toString(),
        description: description,
        success: false
      });
    };

    const exportCSV = async () => {
      try {
        if (interop.isPackaged && api.defaultBackend) {
          const directory = await interop.openDirectory(
            i18n.t('profit_loss_report.select_directory').toString()
          );
          if (!directory) {
            return;
          }
          await createCsv(directory);
        } else {
          const result = await api.downloadCSV();
          if (!result.success) {
            showMessage(
              result.message ??
                i18n.t('profit_loss_report.download_failed').toString()
            );
          }
        }
      } catch (e: any) {
        showMessage(e.message);
      }
    };

    const interop = useInterop();
    const packaged = computed(() => interop.isPackaged);

    return {
      exportCSV,
      packaged
    };
  }
});
</script>
