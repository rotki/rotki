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
    <VDivider />
    <VRow v-if="queue.length > 0" justify="end">
      <VCol cols="auto">
        <VTooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <VBtn icon v-bind="attrs" v-on="on" @click="dismissAll()">
              <VIcon>mdi-notification-clear-all</VIcon>
            </VBtn>
          </template>
          <span>{{ t('notification_popup.dismiss_all') }}</span>
        </VTooltip>
      </VCol>
    </VRow>
    <VTooltip v-if="queue.length > 0" bottom>
      <template #activator="{ on }">
        <div :class="css.wrapper" v-on="on">
          <VBadge
            inline
            :content="queue.length"
            color="info"
            :class="css.count"
          />
        </div>
      </template>
      <span v-text="t('notification_popup.tooltip')" />
    </VTooltip>
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

.count {
  position: absolute;
  right: 4px;
  top: 0;
}

.wrapper {
  position: absolute;
  top: 48px;
  right: 0;
}
</style>
