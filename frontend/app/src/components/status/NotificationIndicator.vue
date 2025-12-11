<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';

defineProps<{
  visible: boolean;
}>();

const emit = defineEmits(['click']);
const { count } = storeToRefs(useNotificationsStore());

function click() {
  emit('click');
}

const { hasRunningTasks } = storeToRefs(useTaskStore());

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiBadge
    :text="count.toString()"
    :model-value="count > 0"
    color="primary"
    placement="top"
    size="sm"
    offset-y="14"
    offset-x="-12"
  >
    <MenuTooltipButton
      :tooltip="t('notification_indicator.tooltip')"
      @click="click()"
    >
      <RuiIcon
        v-if="!hasRunningTasks"
        :class="{ '-rotate-[25deg]': visible }"
        name="lu-bell"
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
