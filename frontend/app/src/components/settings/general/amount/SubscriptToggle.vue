<script setup lang="ts">
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import SettingsOption from '../../controls/SettingsOption.vue';

const { t } = useI18n();
const frontendSettingsStore = useFrontendSettingsStore();
const { subscriptDecimals } = storeToRefs(frontendSettingsStore);
const subscriptEnabled = ref<boolean>(false);

const exampleValues = [
  {
    original: '0.0000000815',
    value: bigNumberify('0.0000000815'),
  },
  {
    original: '0.00000000123',
    value: bigNumberify('0.00000000123'),
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
    <div class="flex flex-col gap-4">
      <RuiSwitch
        v-model="subscriptEnabled"
        data-cy="subscript-toggle-switch"
        color="primary"
        :label="t('rounding_settings.subscript.toggle_label')"
        :hint="t('rounding_settings.subscript.hint')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />

      <div class="ml-6 space-y-3">
        <div
          v-for="example in exampleValues"
          :key="example.original"
          class="flex items-center gap-4"
        >
          <span class="text-rui-text-primary">{{ example.original }}</span>
          <RuiIcon
            name="arrow-right-line"
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
