<script setup lang="ts">
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';

const { t } = useI18n();

const useHistoricalAssetBalances = ref<boolean>(false);
const { useHistoricalAssetBalances: enabled } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(useHistoricalAssetBalances, get(enabled));
});
</script>

<template>
  <RuiMenu
    menu-class="min-w-[18rem] max-w-[20rem]"
    :popper="{ placement: 'top' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        v-bind="attrs"
        size="sm"
        icon
        variant="text"
        class="!p-1"
      >
        <RuiIcon
          name="lu-arrow-up-right"
          size="14"
        />
      </RuiButton>
    </template>

    <div class="p-4">
      <RuiCardHeader class="p-0 mb-2">
        <template #header>
          {{ t('statistics_graph_settings.source.title') }}
        </template>
      </RuiCardHeader>
      <SettingsOption
        #default="{ updateImmediate }"
        setting="useHistoricalAssetBalances"
        frontend-setting
      >
        <RuiRadioGroup
          v-model="useHistoricalAssetBalances"
          color="primary"
          :hint="t('statistics_graph_settings.source.warning')"
          size="sm"
          @update:model-value="updateImmediate($event)"
        >
          <RuiRadio
            :label="t('statistics_graph_settings.source.snapshot')"
            :value="false"
          />
          <RuiRadio
            :label="t('statistics_graph_settings.source.historical_events_processing')"
            :value="true"
          />
        </RuiRadioGroup>
      </SettingsOption>
    </div>
  </RuiMenu>
</template>
