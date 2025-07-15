<script setup lang="ts">
import { bigNumberify } from '@rotki/common';
import { RuiIcon } from '@rotki/ui-library';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import SettingsOption from '../../controls/SettingsOption.vue';

const { t } = useI18n({ useScope: 'global' });
const frontendSettingsStore = useFrontendSettingsStore();
const { subscriptDecimals } = storeToRefs(frontendSettingsStore);
const subscriptEnabled = ref<boolean>(false);

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

onMounted(() => {
  set(subscriptEnabled, get(subscriptDecimals));
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="subscriptDecimals"
    frontend-setting
    :error-message="t('rounding_settings.subscript.error')"
  >
    <div class="flex flex-col space-y-2">
      <div class="flex items-start justify-between">
        <RuiSwitch
          v-model="subscriptEnabled"
          data-cy="subscript-toggle-switch"
          color="primary"
          :label="t('rounding_settings.subscript.toggle_label')"
          :success-messages="success"
          :error-messages="error"
          @update:model-value="updateImmediate($event)"
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
          <AmountDisplay
            :value="example.value"
            :subscript-decimals="subscriptEnabled"
          />
        </div>
      </div>
    </div>
  </SettingsOption>
</template>
