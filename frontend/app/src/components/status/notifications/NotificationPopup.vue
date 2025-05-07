<script setup lang="ts">
import Notification from '@/components/status/notifications/Notification.vue';
import { useNotificationsStore } from '@/store/notifications';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { createNotification } from '@/utils/notifications';

const { t } = useI18n({ useScope: 'global' });

const visibleNotification = ref(createNotification());
const notificationStore = useNotificationsStore();
const { queue } = storeToRefs(notificationStore);
const { displayed } = notificationStore;
const { showNotificationBar } = storeToRefs(useAreaVisibilityStore());

function dismiss(id: number) {
  displayed([id]);
  set(visibleNotification, { ...get(visibleNotification), display: false });
}

function dismissAll() {
  displayed(get(queue).map(({ id }) => id));
  set(visibleNotification, { ...get(visibleNotification), display: false });
}

function checkQueue() {
  if (get(showNotificationBar))
    return;

  const data = [...get(queue)];
  if (!get(visibleNotification).display && data.length > 0) {
    const next = data.shift();
    if (!next)
      return;

    nextTick(() => {
      set(visibleNotification, next);
    });
  }
}

watch(queue, checkQueue, { deep: true, immediate: true });

watch(showNotificationBar, (showNotificationBar) => {
  if (showNotificationBar)
    dismissAll();
});
</script>

<template>
  <RuiNotification
    v-model="visibleNotification.display"
    :timeout="visibleNotification.duration"
    width="400px"
    class="top-[3.5rem]"
    @update:model-value="displayed([visibleNotification.id])"
  >
    <Notification
      popup
      :notification="visibleNotification"
      @dismiss="dismiss(visibleNotification.id)"
    />
    <template v-if="queue.length > 0">
      <div class="flex justify-between p-2 items-center border-t border-default">
        <RuiTooltip
          :open-delay="400"
          :popper="{ placement: 'right' }"
        >
          <template #activator>
            <RuiChip
              class="!p-1.5"
              color="primary"
              size="sm"
            >
              {{ queue.length }}
            </RuiChip>
          </template>
          <span v-text="t('notification_popup.tooltip')" />
        </RuiTooltip>

        <RuiTooltip
          :open-delay="400"
          :popper="{ placement: 'left' }"
        >
          <template #activator>
            <RuiButton
              variant="text"
              class="!p-1.5"
              icon
              @click="dismissAll()"
            >
              <RuiIcon name="lu-list" />
            </RuiButton>
          </template>
          {{ t('notification_popup.dismiss_all') }}
        </RuiTooltip>
      </div>
    </template>
  </RuiNotification>
</template>
