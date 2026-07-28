<script setup lang="ts">
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useSilentNotifications } from '@/modules/core/notifications/use-silent-notifications';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';

defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  click: [];
}>();
const { count } = storeToRefs(useNotificationsStore());

function click() {
  emit('click');
}

const { hasRunningTasks } = storeToRefs(useTaskStore());
const { silent } = useSilentNotifications();

const { t } = useI18n({ useScope: 'global' });

const tooltip = computed<string>(() => get(silent)
  ? t('notification_indicator.tooltip_silent')
  : t('notification_indicator.tooltip'));
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
      :tooltip="tooltip"
      @click="click()"
    >
      <RuiIcon
        v-if="!hasRunningTasks"
        :class="{ '-rotate-[25deg]': visible }"
        :name="silent ? 'lu-bell-off' : 'lu-bell'"
        data-testid="notification-indicator-icon"
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
