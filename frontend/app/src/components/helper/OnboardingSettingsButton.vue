<script setup lang="ts">
const { t } = useI18n();
const visible = ref<boolean>(false);
const { connected } = toRefs(useMainStore());
</script>

<template>
  <div>
    <RuiTooltip
      :text="t('backend_settings_button.tooltip')"
      :popper="{ placement: 'top', offsetDistance: 0 }"
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
          <RuiIcon name="settings-4-line" />
        </RuiButton>
      </template>
    </RuiTooltip>
    <OnboardingSettings v-if="visible" @dismiss="visible = false" />
  </div>
</template>
