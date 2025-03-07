<script setup lang="ts">
import type { ProfitLossReportPeriod } from '@/types/reports';
import RangeSelector from '@/components/helper/date/RangeSelector.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { Routes } from '@/router/routes';
import { convertToTimestamp } from '@/utils/date';
import { checkIfDevelopment } from '@shared/utils';

const emit = defineEmits<{
  (e: 'generate', data: ProfitLossReportPeriod): void;
  (e: 'export-data', data: ProfitLossReportPeriod): void;
  (e: 'import-data'): void;
}>();

const { t } = useI18n();

const range = ref({ end: '', start: '' });
const valid = ref<boolean>(false);

const startTimestamp = computed<number>(() => convertToTimestamp(get(range).start));

const endTimestamp = computed<number>(() => convertToTimestamp(get(range).end));

function generate() {
  emit('generate', {
    end: get(endTimestamp),
    start: get(startTimestamp),
  });
}

function exportReportData() {
  emit('export-data', {
    end: get(endTimestamp),
    start: get(startTimestamp),
  });
}

function importReportData() {
  emit('import-data');
}

const isDevelopment = checkIfDevelopment();
const isDemoMode = import.meta.env.VITE_DEMO_MODE !== undefined;
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
                <RuiIcon name="lu-settings" />
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
              <RuiIcon name="lu-scroll-text" />
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
                :disabled="isDevelopment && !isDemoMode"
                class="h-full"
              >
                <template #activator>
                  <RuiButton
                    size="lg"
                    v-bind="attrs"
                  >
                    <template #prepend>
                      <RuiIcon name="lu-bug" />
                    </template>
                    <span v-if="isDevelopment && !isDemoMode">
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
                  <RuiIcon name="lu-file-down" />
                </template>
                {{ t('profit_loss_reports.debug.export_data') }}
              </RuiButton>
              <RuiButton
                variant="list"
                @click="importReportData()"
              >
                <template #prepend>
                  <RuiIcon name="lu-file-up" />
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
