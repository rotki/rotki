<script setup lang="ts">
defineProps<{
  visible: boolean;
}>();

const emit = defineEmits(['click']);
const { count } = storeToRefs(useNotificationsStore());
const click = () => {
  emit('click');
};

const { hasRunningTasks } = storeToRefs(useTaskStore());

const { t } = useI18n();
</script>

<template>
  <RuiBadge
    :text="count.toString()"
    :value="count > 0"
    color="primary"
    placement="top"
    offset-y="14"
    offset-x="-12"
  >
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
      <div
        v-else
        class="flex items-center"
        data-cy="notification-indicator-progress"
      >
        <RuiProgress variant="indeterminate" circular size="20" thickness="2" />
      </div>
    </MenuTooltipButton>
  </RuiBadge>
</template>

<style module lang="scss">
.visible {
  transform: rotate(-25deg);
}
</style>
