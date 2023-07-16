<script setup lang="ts">
const visible = ref<boolean>(false);
const { connected } = toRefs(useMainStore());

const { t } = useI18n();
</script>

<template>
  <VBottomSheet v-model="visible" width="98%" class="backend-settings-button">
    <template #activator="{ on: menu, attrs }">
      <VTooltip left max-width="280">
        <template #activator="{ on: tooltip }">
          <VBtn
            v-bind="attrs"
            text
            fab
            depressed
            :disabled="!connected"
            color="primary"
            v-on="{ ...menu, ...tooltip }"
          >
            <VIcon>mdi-cog</VIcon>
          </VBtn>
        </template>
        <span>{{ t('backend_settings_button.tooltip') }}</span>
      </VTooltip>
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
