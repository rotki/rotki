<script setup lang="ts">
import { storeToRefs } from 'pinia';
import AmountInput from '@/components/inputs/AmountInput.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const { t } = useI18n({ useScope: 'global' });

const { assetMovementAmountTolerance } = storeToRefs(useGeneralSettingsStore());

const showMenu = ref<boolean>(false);
const toleranceValue = ref<string>('');

function resetToleranceState(): void {
  set(toleranceValue, get(assetMovementAmountTolerance));
}

onMounted(() => {
  resetToleranceState();
});
</script>

<template>
  <RuiMenu
    v-model="showMenu"
    menu-class="w-full max-w-80"
    :popper="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            v-bind="attrs"
            class="!rounded-l-none !px-2 h-9"
          >
            <RuiIcon
              name="lu-settings"
              size="20"
            />
          </RuiButton>
        </template>
        <span>{{ t('asset_movement_matching.settings.tooltip') }}</span>
      </RuiTooltip>
    </template>
    <div class="p-4">
      <div class="text-subtitle-1 font-medium mb-4">
        {{ t('asset_movement_matching.settings.title') }}
      </div>
      <SettingsOption
        #default="{ update, error, success }"
        setting="assetMovementAmountTolerance"
        @finished="resetToleranceState()"
      >
        <AmountInput
          v-model="toleranceValue"
          variant="outlined"
          :label="t('asset_movement_matching.settings.amount_tolerance.label')"
          :hint="t('asset_movement_matching.settings.amount_tolerance.hint')"
          :error-messages="error"
          :success-messages="success"
          @update:model-value="update($event)"
        />
      </SettingsOption>
      <div class="flex justify-end mt-4">
        <RuiButton
          variant="text"
          color="primary"
          @click="showMenu = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>
