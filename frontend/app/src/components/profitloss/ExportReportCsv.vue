<script setup lang="ts">
withDefaults(
  defineProps<{
    icon?: boolean;
  }>(),
  {
    icon: false
  }
);

const { createCsv } = useReportsStore();
const { setMessage } = useMessageStore();

const { t } = useI18n();
const { appSession, openDirectory } = useInterop();

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
    if (appSession) {
      const directory = await openDirectory(
        t('common.select_directory').toString()
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

const [DefineButton, ReuseButton] = createReusableTemplate();

const label = computed(() =>
  appSession ? t('common.actions.export_csv') : t('common.actions.download_csv')
);
</script>

<template>
  <span>
    <DefineButton>
      <RuiButton
        :size="icon ? 'sm' : undefined"
        :variant="icon ? 'text' : 'default'"
        :icon="icon"
        color="primary"
        @click="exportCSV()"
      >
        <div class="flex items-center gap-2">
          <RuiIcon size="20" name="file-download-line" />
          <span v-if="!icon">{{ label }}</span>
        </div>
      </RuiButton>
    </DefineButton>
    <span v-if="icon">
      <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
        <template #activator>
          <ReuseButton />
        </template>
        <span> {{ label }} </span>
      </RuiTooltip>
    </span>
    <ReuseButton v-else />
  </span>
</template>
