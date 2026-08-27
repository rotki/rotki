<script setup lang="ts">
import { useMainStore } from '@/modules/core/common/use-main-store';
import OnboardingSettings from '@/modules/settings/OnboardingSettings.vue';

const { t } = useI18n({ useScope: 'global' });
const visible = ref<boolean>(false);
const { connected } = storeToRefs(useMainStore());
</script>

<template>
  <div>
    <RuiTooltip
      :text="t('backend_settings_button.tooltip')"
      :options="{ offset: 0, placement: 'top' }"
      :class-names="{ tooltip: 'max-w-[12rem]' }"
    >
      <template #activator>
        <RuiButton
          :disabled="!connected"
          variant="text"
          color="primary"
          icon
          rounded
          @click="visible = true"
        >
          <RuiIcon name="lu-settings" />
        </RuiButton>
      </template>
    </RuiTooltip>
    <OnboardingSettings
      v-if="visible"
      @dismiss="visible = false"
    />
  </div>
</template>
