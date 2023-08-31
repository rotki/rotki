<script setup lang="ts">
const { t } = useI18n();
const visible = ref<boolean>(false);
const { connected } = toRefs(useMainStore());
</script>

<template>
  <VBottomSheet v-model="visible" width="98%" class="backend-settings-button">
    <template #activator="{ attrs }">
      <RuiTooltip
        v-bind="attrs"
        :disabled="!connected"
        :text="t('backend_settings_button.tooltip')"
      >
        <RuiButton
          variant="text"
          color="primary"
          icon
          rounded
          @click="visible = true"
        >
          <RuiIcon name="settings-4-line" />
        </RuiButton>
      </RuiTooltip>
    </template>
    <OnboardingSettings v-if="visible" @dismiss="visible = false" />
  </VBottomSheet>
</template>

<style scoped lang="scss">
:deep(.v-card) {
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}

.backend-settings-button {
  height: calc(100vh - 80px);
}
</style>
