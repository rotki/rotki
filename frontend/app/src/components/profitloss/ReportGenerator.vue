<script setup lang="ts">
import { type ProfitLossReportPeriod } from '@/types/reports';
import { Routes } from '@/router/routes';

const emit = defineEmits<{
  (e: 'generate', data: ProfitLossReportPeriod): void;
  (e: 'export-data', data: ProfitLossReportPeriod): void;
  (e: 'import-data'): void;
}>();

const { t } = useI18n();

const range = ref({ start: '', end: '' });
const valid = ref<boolean>(false);

const startTimestamp = computed<number>(() =>
  convertToTimestamp(get(range).start)
);

const endTimestamp = computed<number>(() => convertToTimestamp(get(range).end));

const generate = () => {
  emit('generate', {
    start: get(startTimestamp),
    end: get(endTimestamp)
  });
};

const exportReportData = () => {
  emit('export-data', {
    start: get(startTimestamp),
    end: get(endTimestamp)
  });
};

const importReportData = () => {
  emit('import-data');
};

const isDevelopment = checkIfDevelopment();
const accountSettingsRoute = Routes.SETTINGS_ACCOUNTING;
</script>

<template>
  <Card>
    <template #title>
      {{ t('common.actions.generate') }}
    </template>
    <template #details>
      <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
        <template #activator>
          <RouterLink :to="accountSettingsRoute">
            <RuiButton variant="text" icon color="primary">
              <RuiIcon name="settings-3-line" />
            </RuiButton>
          </RouterLink>
        </template>
        <span>{{ t('profit_loss_report.settings_tooltip') }}</span>
      </RuiTooltip>
    </template>
    <RangeSelector v-model="range" @update:valid="valid = $event" />
    <template #buttons>
      <div class="flex gap-4 w-full">
        <div class="grow">
          <RuiButton
            class="w-full"
            color="primary"
            size="lg"
            :disabled="!valid"
            @click="generate()"
          >
            <template #prepend>
              <RuiIcon name="file-list-3-line" />
            </template>
            {{ t('common.actions.generate') }}
          </RuiButton>
        </div>
        <div>
          <VMenu v-if="isDevelopment" offset-y left>
            <template #activator="{ on }">
              <RuiButton size="lg" v-on="on">
                <template #prepend>
                  <RuiIcon name="file-settings-line" />
                </template>
                {{ t('profit_loss_reports.debug.title') }}
              </RuiButton>
            </template>
            <VList>
              <VListItem link @click="exportReportData()">
                <VListItemTitle>
                  <div class="flex items-center">
                    <RuiIcon class="mr-2" name="file-download-line" />
                    <span>
                      {{ t('profit_loss_reports.debug.export_data') }}
                    </span>
                  </div>
                </VListItemTitle>
              </VListItem>
              <VListItem link @click="importReportData()">
                <VListItemTitle>
                  <div class="flex items-center">
                    <RuiIcon class="mr-2" name="file-upload-line" />
                    <span>
                      {{ t('profit_loss_reports.debug.import_data') }}
                    </span>
                  </div>
                </VListItemTitle>
              </VListItem>
            </VList>
          </VMenu>
          <RuiButton v-else size="lg" @click="exportReportData()">
            <template #prepend>
              <RuiIcon name="file-download-line" />
            </template>
            {{ t('profit_loss_reports.debug.export_data') }}
          </RuiButton>
        </div>
      </div>
    </template>
  </Card>
</template>
