<script setup lang="ts">
import { useSilentNotifications } from '@/modules/core/notifications/use-silent-notifications';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import { useNotificationBadge } from '@/modules/shell/components/use-notification-badge';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  click: [];
}>();
const { actionCount, color: badgeColor, hasUnread, text: badgeText, visible: badgeVisible } = useNotificationBadge();

function click() {
  emit('click');
}

const { isActive: hasRunningTasks } = useTaskCenter();
const { silent } = useSilentNotifications();

const { t } = useI18n({ useScope: 'global' });

/**
 * Says what the badge means, since a dot says nothing on its own.
 *
 * @remarks
 * Doubles as the button's accessible name: the count reaches a screen reader as a bare number and
 * the dot does not reach it at all, so without this the badge is a purely visual signal.
 */
const tooltip = computed<string>(() => {
  if (get(silent))
    return t('notification_indicator.tooltip_silent');

  const count = get(actionCount);
  if (count > 0)
    return t('notification_indicator.tooltip_action', { count }, count);

  if (get(hasUnread))
    return t('notification_indicator.tooltip_unread');

  return t('notification_indicator.tooltip');
});
</script>

<template>
  <RuiBadge
    :text="badgeText"
    :dot="!badgeText"
    :model-value="badgeVisible"
    :color="badgeColor"
    placement="top"
    size="sm"
    offset-y="14"
    offset-x="-12"
    data-testid="notification-indicator-badge"
  >
    <MenuTooltipButton
      :tooltip="tooltip"
      :aria-label="tooltip"
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
        data-testid="notification-indicator-progress"
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
