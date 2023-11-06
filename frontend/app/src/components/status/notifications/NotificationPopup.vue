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
      <div class="flex justify-end border-t border-default">
        <RuiTooltip open-delay="400">
          <template #activator>
            <RuiButton variant="text" class="!p-2" icon @click="dismissAll()">
              <RuiIcon name="menu-unfold-line" />
            </RuiButton>
          </template>
          {{ t('notification_popup.dismiss_all') }}
        </RuiTooltip>
      </div>
      <div class="absolute top-16 right-6">
        <RuiTooltip open-delay="400">
          <template #activator>
            <RuiBadge :text="queue.length" color="info" />
          </template>
          <span v-text="t('notification_popup.tooltip')" />
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
