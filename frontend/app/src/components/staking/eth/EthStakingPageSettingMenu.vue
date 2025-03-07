<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const { t } = useI18n();
const value = ref(false);

const { shouldRefreshValidatorDailyStats } = storeToRefs(useFrontendSettingsStore());

function setValue() {
  set(value, get(shouldRefreshValidatorDailyStats));
}

onBeforeMount(() => {
  setValue();
});
</script>

<template>
  <RuiMenu
    menu-class="max-w-[20rem] [&>div]:h-[8rem]"
    :popper="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        class="!p-2"
        v-bind="attrs"
      >
        <RuiIcon name="lu-settings" />
      </RuiButton>
    </template>

    <RuiCard
      variant="flat"
      class="!bg-transparent [&>div]:h-full"
    >
      <SettingsOption
        #default="{ error, success, updateImmediate }"
        setting="shouldRefreshValidatorDailyStats"
        frontend-setting
        @finished="setValue()"
      >
        <RuiSwitch
          :hint="t('eth2_page.setting.refresh_validator_daily_stats_on_load.hint')"
          :model-value="value"
          color="primary"
          :success-messages="success"
          :error-messages="error"
          @update:model-value="updateImmediate($event)"
        >
          {{ t('eth2_page.setting.refresh_validator_daily_stats_on_load.title') }}
        </RuiSwitch>
      </SettingsOption>
    </RuiCard>
  </RuiMenu>
</template>
