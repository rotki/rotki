<script setup lang="ts">
const { t } = useI18n();

const emit = defineEmits<{
  (e: 'updated'): void;
}>();

const updated = () => emit('updated');

const inferZeroTimedBalances = ref<boolean>(false);
const { inferZeroTimedBalances: enabled } = storeToRefs(
  useGeneralSettingsStore()
);

const resetState = () => {
  set(inferZeroTimedBalances, get(enabled));
};

const finished = () => {
  resetState();
  updated();
};

onMounted(() => {
  resetState();
});
</script>

<template>
  <div>
    <card-title class="font-weight-medium mb-2">
      {{ t('statistics_graph_settings.infer_zero_timed_balances.title') }}
    </card-title>
    <settings-option
      #default="{ error, success, update }"
      setting="inferZeroTimedBalances"
      @finished="finished()"
    >
      <v-switch
        v-model="inferZeroTimedBalances"
        :label="t('statistics_graph_settings.infer_zero_timed_balances.label')"
        persistent-hint
        :success-messages="success"
        :error-messages="error"
        @change="update($event)"
      />
    </settings-option>
  </div>
</template>
