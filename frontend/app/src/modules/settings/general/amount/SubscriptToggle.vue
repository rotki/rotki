<script setup lang="ts">
import { bigNumberify } from '@rotki/common';
import { RuiIcon } from '@rotki/ui-library';
import { ValueDisplay } from '@/modules/assets/amount-display';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';

const { t } = useI18n({ useScope: 'global' });

const exampleValues = [
  {
    original: '0.0000000875',
    value: bigNumberify('0.0000000875'),
  },
  {
    original: '0.000000001234',
    value: bigNumberify('0.000000001234'),
  },
];
</script>

<template>
  <div class="flex flex-col space-y-2">
    <div class="flex items-start justify-between">
      <SettingSwitch
        setting="subscriptDecimals"
        data-testid="subscript-toggle-switch"
        :label="t('rounding_settings.subscript.toggle_label')"
        :error-message="t('rounding_settings.subscript.error')"
      />
      <HintMenuIcon class="-mt-3 mr-2">
        {{ t('rounding_settings.subscript.hint') }}
      </HintMenuIcon>
    </div>
    <div class="space-y-2">
      <div
        v-for="example in exampleValues"
        :key="example.original"
        class="flex items-center gap-3 ml-1"
      >
        <span class="text-rui-text-primary">{{ example.original }}</span>
        <RuiIcon
          name="lu-arrow-right"
          class="text-rui-text-secondary"
        />
        <ValueDisplay :value="example.value" />
      </div>
    </div>
  </div>
</template>
