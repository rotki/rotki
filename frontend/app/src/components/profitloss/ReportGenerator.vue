<script setup lang="ts">
const emit = defineEmits(['generate', 'export-data', 'import-data']);

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
</script>

<template>
  <VForm :value="valid">
    <Card>
      <template #title>
        {{ t('common.actions.generate') }}
      </template>
      <template #details>
        <VTooltip top>
          <template #activator="{ on, attrs }">
            <RuiButton v-bind="attrs" to="/settings/accounting" v-on="on">
              <VIcon color="primary">mdi-cog</VIcon>
            </RuiButton>
          </template>
          <span>{{ t('profit_loss_report.settings_tooltip') }}</span>
        </VTooltip>
      </template>
      <RangeSelector v-model="range" @update:valid="valid = $event" />
      <template #buttons>
        <VRow no-gutters>
          <VCol>
            <RuiButton
              color="primary"
              class="px-8 w-full"
              large
              :disabled="!valid"
              @click="generate()"
            >
              <VIcon class="mr-2">mdi-file-chart</VIcon>
              {{ t('common.actions.generate') }}
            </RuiButton>
          </VCol>
          <VCol cols="auto">
            <VMenu v-if="isDevelopment" offset-y left>
              <template #activator="{ on }">
                <RuiButton color="warning" large class="px-4 ml-4" v-on="on">
                  <VIcon class="mr-2">mdi-wrench</VIcon>
                  {{ t('profit_loss_reports.debug.title') }}
                </RuiButton>
              </template>
              <VList>
                <VListItem link @click="exportReportData()">
                  <VListItemTitle>
                    <div class="flex items-center">
                      <VIcon class="mr-2">mdi-export</VIcon>
                      <span>
                        {{ t('profit_loss_reports.debug.export_data') }}
                      </span>
                    </div>
                  </VListItemTitle>
                </VListItem>
                <VListItem link @click="importReportData()">
                  <VListItemTitle>
                    <div class="flex items-center">
                      <VIcon class="mr-2">mdi-import</VIcon>
                      <span>
                        {{ t('profit_loss_reports.debug.import_data') }}
                      </span>
                    </div>
                  </VListItemTitle>
                </VListItem>
              </VList>
            </VMenu>
            <RuiButton
              v-else
              color="warning"
              large
              class="px-4 ml-4"
              @click="exportReportData()"
            >
              <VIcon class="mr-2">mdi-export</VIcon>
              {{ t('profit_loss_reports.debug.export_data') }}
            </RuiButton>
          </VCol>
        </VRow>
      </template>
    </Card>
  </VForm>
</template>
