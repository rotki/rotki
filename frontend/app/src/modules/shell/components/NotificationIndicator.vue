<script setup lang="ts">
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useSilentNotifications } from '@/modules/core/notifications/use-silent-notifications';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';

defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  click: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { hasUnread } = storeToRefs(useNotificationsStore());

const { silent } = useSilentNotifications();

/**
 * Says what the dot means, since a dot says nothing on its own.
 *
 * @remarks
 * Doubles as the button's accessible name: the dot does not reach a screen reader at all, so
 * without this it is a purely visual signal.
 */
const tooltip = computed<string>(() => {
  if (get(silent))
    return t('notification_indicator.tooltip_silent');

  if (get(hasUnread))
    return t('notification_indicator.tooltip_unread');

  return t('notification_indicator.tooltip');
});

function click(): void {
  emit('click');
}
</script>

<template>
  <RuiBadge
    :model-value="hasUnread"
    dot
    color="primary"
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
        :class="{ '-rotate-[25deg]': visible }"
        :name="silent ? 'lu-bell-off' : 'lu-bell'"
        data-testid="notification-indicator-icon"
      />
    </MenuTooltipButton>
  </RuiBadge>
</template>
