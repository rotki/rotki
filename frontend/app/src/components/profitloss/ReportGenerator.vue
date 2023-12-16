<script setup lang="ts">
import { Routes } from '@/router/routes';
import type { ProfitLossReportPeriod } from '@/types/reports';

const emit = defineEmits<{
  (e: 'generate', data: ProfitLossReportPeriod): void;
  (e: 'export-data', data: ProfitLossReportPeriod): void;
  (e: 'import-data'): void;
}>();

const { t } = useI18n();

const range = ref({ start: '', end: '' });
const valid = ref<boolean>(false);

const startTimestamp = computed<number>(() => convertToTimestamp(get(range).start));

const endTimestamp = computed<number>(() => convertToTimestamp(get(range).end));

function generate() {
  emit('generate', {
    start: get(startTimestamp),
    end: get(endTimestamp),
  });
}

function exportReportData() {
  emit('export-data', {
    start: get(startTimestamp),
    end: get(endTimestamp),
  });
}

function importReportData() {
  emit('import-data');
}

const isDevelopment = checkIfDevelopment();
const accountSettingsRoute = Routes.SETTINGS_ACCOUNTING;
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex justify-between px-4 py-2">
        <CardTitle>
          {{ t('common.actions.generate') }}
        </CardTitle>
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RouterLink :to="accountSettingsRoute">
              <RuiButton
                variant="text"
                icon
                color="primary"
              >
                <RuiIcon name="settings-3-line" />
              </RuiButton>
            </RouterLink>
          </template>
          <span>{{ t('profit_loss_report.settings_tooltip') }}</span>
        </RuiTooltip>
      </div>
    </template>
    <RangeSelector
      v-model="range"
      @update:valid="valid = $event"
    />
    <template #footer>
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
        <div class="">
          <RuiMenu
            close-on-content-click
            :popper="{ placement: 'bottom-end' }"
          >
            <template #activator="{ attrs }">
              <RuiTooltip
                :open-delay="400"
                :popper="{ placement: 'top' }"
                :disabled="isDevelopment"
                class="h-full"
              >
                <template #activator>
                  <RuiButton
                    size="lg"
                    v-bind="attrs"
                  >
                    <template #prepend>
                      <RuiIcon name="bug-line" />
                    </template>
                    <span v-if="isDevelopment">
                      {{ t('profit_loss_reports.debug.title') }}
                    </span>
                  </RuiButton>
                </template>

                {{ t('profit_loss_reports.debug.title') }}
              </RuiTooltip>
            </template>
            <div class="py-2">
              <RuiButton
                variant="list"
                @click="exportReportData()"
              >
                <template #prepend>
                  <RuiIcon name="file-download-line" />
                </template>
                {{ t('profit_loss_reports.debug.export_data') }}
              </RuiButton>
              <RuiButton
                variant="list"
                @click="importReportData()"
              >
                <template #prepend>
                  <RuiIcon name="file-upload-line" />
                </template>
                {{ t('profit_loss_reports.debug.import_data') }}
              </RuiButton>
            </div>
          </RuiMenu>
        </div>
      </div>
    </template>
  </RuiCard>
</template>
