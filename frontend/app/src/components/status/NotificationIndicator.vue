<script setup lang="ts">
defineProps<{
  visible: boolean;
}>();

const emit = defineEmits(['click']);
const { count } = storeToRefs(useNotificationsStore());

function click() {
  emit('click');
}

const { hasRunningTasks } = storeToRefs(useTaskStore());

const { t } = useI18n();

const css = useCssModule();
</script>

<template>
  <RuiBadge
    :text="count.toString()"
    :model-value="count > 0"
    color="primary"
    placement="top"
    offset-y="14"
    offset-x="-12"
  >
    <MenuTooltipButton
      :tooltip="t('notification_indicator.tooltip')"
      @click="click()"
    >
      <RuiIcon
        v-if="!hasRunningTasks"
        :class="{
          [css.visible]: visible,
        }"
        name="notification-3-line"
      />
      <div
        v-else
        class="flex items-center"
        data-cy="notification-indicator-progress"
      >
        <RuiProgress
          variant="indeterminate"
          circular
          size="20"
          thickness="2"
        />
      </div>
    </MenuTooltipButton>
  </RuiBadge>
</template>

<style module lang="scss">
.visible {
  transform: rotate(-25deg);
}
</style>
