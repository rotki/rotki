<script setup lang="ts">
const { t } = useI18n();

const visibleNotification = ref(createNotification());
const notificationStore = useNotificationsStore();
const { queue } = storeToRefs(notificationStore);
const css = useCssModule();
const { displayed } = notificationStore;

const dismiss = async (id: number) => {
  await displayed([id]);
  set(visibleNotification, { ...get(visibleNotification), display: false });
};

const dismissAll = async () => {
  await displayed(get(queue).map(({ id }) => id));
  set(visibleNotification, { ...get(visibleNotification), display: false });
};

const checkQueue = () => {
  const data = [...get(queue)];
  if (!get(visibleNotification).display && data.length > 0) {
    const next = data.shift();
    if (!next) {
      return;
    }
    nextTick(() => {
      set(visibleNotification, next);
    });
  }
};

watch(queue, checkQueue, { deep: true });

onMounted(() => {
  checkQueue();
});

const { dark } = useTheme();
</script>

<template>
  <VSnackbar
    v-model="visibleNotification.display"
    :class="css.popup"
    :timeout="visibleNotification.duration"
    top
    right
    :light="!dark"
    app
    rounded
    width="400px"
    @input="displayed([visibleNotification.id])"
  >
    <Notification
      popup
      :notification="visibleNotification"
      @dismiss="dismiss(visibleNotification.id)"
    />
    <template v-if="queue.length > 0">
      <div
        class="flex justify-between p-2 items-center border-t border-default"
      >
        <RuiTooltip open-delay="400" :popper="{ placement: 'right' }">
          <template #activator>
            <RuiChip class="!p-1.5" color="primary" size="sm">
              {{ queue.length }}
            </RuiChip>
          </template>
          <span v-text="t('notification_popup.tooltip')" />
        </RuiTooltip>

        <RuiTooltip open-delay="400" :popper="{ placement: 'left' }">
          <template #activator>
            <RuiButton variant="text" class="!p-1.5" icon @click="dismissAll()">
              <RuiIcon name="list-unordered" />
            </RuiButton>
          </template>
          {{ t('notification_popup.dismiss_all') }}
        </RuiTooltip>
      </div>
    </template>
  </VSnackbar>
</template>

<style module lang="scss">
.popup {
  :global {
    .v-snack {
      &__wrapper {
        width: 400px;
      }

      &__content {
        padding: 0 !important;
      }

      &__action {
        margin-right: 0 !important;
      }
    }
  }
}
</style>
