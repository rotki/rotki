<script setup lang="ts">
import OnboardingSettings from '@/components/settings/OnboardingSettings.vue';
import { useMainStore } from '@/store/main';

const { t } = useI18n({ useScope: 'global' });
const visible = ref<boolean>(false);
const { connected } = toRefs(useMainStore());
</script>

<template>
  <div>
    <RuiTooltip
      :text="t('backend_settings_button.tooltip')"
      :popper="{ placement: 'top', offsetDistance: 0 }"
      tooltip-class="max-w-[12rem]"
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
