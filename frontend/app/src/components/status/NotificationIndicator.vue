<script setup lang="ts">
defineProps({
  visible: { required: true, type: Boolean }
});

const emit = defineEmits(['click']);
const { count } = storeToRefs(useNotificationsStore());
const click = () => {
  emit('click');
};

const { hasRunningTasks } = storeToRefs(useTaskStore());

const { t } = useI18n();
</script>

<template>
  <VBadge
    :value="count"
    color="primary"
    right
    overlap
    :class="$style.indicator"
  >
    <template #badge>
      <span>{{ count }}</span>
    </template>
    <MenuTooltipButton
      :tooltip="t('notification_indicator.tooltip')"
      class-name="secondary--text text--lighten-4"
      @click="click()"
    >
      <RuiIcon
        v-if="!hasRunningTasks"
        :class="{
          [$style.visible]: visible
        }"
        name="notification-3-line"
      />
      <VIcon v-else> mdi-spin mdi-loading </VIcon>
    </MenuTooltipButton>
  </VBadge>
</template>

<style module lang="scss">
.indicator {
  :global {
    .v-badge {
      &__badge {
        bottom: calc(100% - 20px) !important;
        left: calc(100% - 20px) !important;
      }
    }
  }
}

.visible {
  transform: rotate(-25deg);
}
</style>
