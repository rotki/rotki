<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const emit = defineEmits<{
  (e: 'updated'): void;
}>();

const { t } = useI18n();

const updated = () => emit('updated');

const inferZeroTimedBalances = ref<boolean>(false);
const { inferZeroTimedBalances: enabled } = storeToRefs(useGeneralSettingsStore());

function resetState() {
  set(inferZeroTimedBalances, get(enabled));
}

function finished() {
  resetState();
  updated();
}

onMounted(() => {
  resetState();
});
</script>

<template>
  <div>
    <CardTitle>
      {{ t('statistics_graph_settings.infer_zero_timed_balances.title') }}
    </CardTitle>
    <SettingsOption
      #default="{ error, success, update }"
      setting="inferZeroTimedBalances"
      @finished="finished()"
    >
      <RuiSwitch
        v-model="inferZeroTimedBalances"
        :label="t('statistics_graph_settings.infer_zero_timed_balances.label')"
        color="primary"
        class="mt-4 [&_span]:!text-sm"
        size="sm"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="update($event)"
      />
    </SettingsOption>
  </div>
</template>
