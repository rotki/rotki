<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAssetStatisticState } from '@/composables/settings/use-asset-statistic-state';

const props = defineProps<{
  asset?: string;
}>();

const emit = defineEmits<{
  preference: [preference?: 'events' | 'snapshot'];
}>();

const { asset } = toRefs(props);

const {
  getPreference,
  name,
  rememberStateForAsset,
  suppressIfPerAsset,
  useHistoricalAssetBalances,
} = useAssetStatisticState(asset);

const { t } = useI18n();

watch(useHistoricalAssetBalances, () => {
  if (!isDefined(asset) || !get(rememberStateForAsset)) {
    return;
  }

  emit('preference', getPreference(get(asset)));
});

watchImmediate(asset, (asset) => {
  if (!asset || !get(rememberStateForAsset)) {
    return;
  }

  emit('preference', getPreference(asset));
});
</script>

<template>
  <RuiMenu
    menu-class="min-w-[18rem] max-w-[20rem]"
    :popper="{ placement: 'top' }"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="t('statistics_graph_settings.source.title')"
        class-name="graph-period"
        custom-color
        v-bind="attrs"
      >
        <RuiIcon name="lu-file-cog" />
      </MenuTooltipButton>
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
          @update:model-value="suppressIfPerAsset(() => updateImmediate($event))"
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
      <RuiCheckbox
        v-if="asset"
        v-model="rememberStateForAsset"
        hide-details
        class="mt-3"
        color="primary"
        :label="t('statistics_graph_settings.source.remember_state_for_asset', { asset: name })"
      />
    </div>
  </RuiMenu>
</template>
