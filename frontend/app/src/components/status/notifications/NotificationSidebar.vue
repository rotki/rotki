<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library-compat';
import { Priority, Severity } from '@rotki/common/lib/messages';
import { Routes } from '@/router/routes';

defineProps<{ visible: boolean }>();

const emit = defineEmits(['close']);

const { t } = useI18n();

const css = useCssModule();

const confirmStore = useConfirmStore();
const { visible: dialogVisible } = storeToRefs(confirmStore);
const { show } = confirmStore;

const notificationStore = useNotificationsStore();
const { prioritized: allNotifications } = storeToRefs(notificationStore);
const { remove } = notificationStore;

function close() {
  emit('close');
}

function input(visible: boolean) {
  if (visible)
    return;

  close();
}

function clear() {
  notificationStore.$reset();
  close();
}

function showConfirmation() {
  show(
    {
      title: t('notification_sidebar.confirmation.title'),
      message: t('notification_sidebar.confirmation.message'),
      type: 'info',
    },
    clear,
  );
}

const { isMdAndDown } = useBreakpoint();
const { hasRunningTasks } = storeToRefs(useTaskStore());

enum TabCategory {
  VIEW_ALL = 'view_all',
  NEEDS_ACTION = 'needs_action',
  REMINDER = 'reminder',
  ERROR = 'error',
}

const tabCategoriesLabel = computed(() => ({
  [TabCategory.VIEW_ALL]: t('notification_sidebar.tabs.view_all'),
  [TabCategory.NEEDS_ACTION]: t('notification_sidebar.tabs.needs_action'),
  [TabCategory.REMINDER]: t('notification_sidebar.tabs.reminder'),
  [TabCategory.ERROR]: t('notification_sidebar.tabs.error'),
}));

const selectedTab: Ref<TabCategory> = ref(TabCategory.VIEW_ALL);

const selectedNotifications = computed(() => {
  const all = get(allNotifications);
  const tab = get(selectedTab);

  if (tab === TabCategory.NEEDS_ACTION)
    return all.filter(item => item.priority === Priority.ACTION);

  if (tab === TabCategory.ERROR)
    return all.filter(item => item.severity === Severity.ERROR);

  if (tab === TabCategory.REMINDER)
    return all.filter(item => item.severity === Severity.REMINDER);

  return all;
});

const itemHeight = 170;
const margin = 6;

const { list, containerProps, wrapperProps } = useVirtualList(selectedNotifications, {
  itemHeight,
});

const notificationStyle = {
  height: `${itemHeight - margin}px`,
  marginTop: `${margin}px`,
};

const [DefineNoMessages, ReuseNoMessages] = createReusableTemplate();
</script>

<template>
  <VNavigationDrawer
    :class="{ [css.mobile]: isMdAndDown, [css.sidebar]: true }"
    width="400px"
    absolute
    clipped
    :value="visible"
    :stateless="dialogVisible"
    right
    temporary
    hide-overlay
    @input="input($event)"
  >
    <DefineNoMessages>
      <div :class="css['no-messages']">
        <RuiIcon
          size="64px"
          color="primary"
          name="information-line"
        />
        <div class="text-rui-text text-lg mt-2">
          {{ t('notification_sidebar.no_messages') }}
        </div>
      </div>
    </DefineNoMessages>
    <div
      class="h-full overflow-hidden flex flex-col"
    >
      <div class="flex justify-between items-center p-2 pl-4">
        <div class="text-h6">
          {{ t('notification_sidebar.title') }}
        </div>
        <RuiButton
          variant="text"
          icon
          @click="close()"
        >
          <RuiIcon name="close-line" />
        </RuiButton>
      </div>

      <ReuseNoMessages v-if="!hasRunningTasks && allNotifications.length === 0" />
      <div
        v-else
        :class="css.messages"
      >
        <PendingTasks />
        <div class="border-b border-default mx-4">
          <RuiTabs
            v-model="selectedTab"
            color="primary"
          >
            <template #default>
              <RuiTab
                v-for="item in Object.values(TabCategory)"
                :key="item"
                size="sm"
                class="!min-w-0"
                :tab-value="item"
              >
                {{ tabCategoriesLabel[item] }}
              </RuiTab>
            </template>
          </RuiTabs>
        </div>
        <div
          v-if="selectedNotifications.length > 0"
          :class="css.content"
          class="!overflow-y-scroll pt-1"
          v-bind="containerProps"
          @scroll="containerProps.onScroll"
        >
          <div v-bind="wrapperProps">
            <Notification
              v-for="item in list"
              :key="item.data.id"
              :notification="item.data"
              :style="notificationStyle"
              @dismiss="remove($event)"
            />
          </div>
        </div>
        <ReuseNoMessages v-else />
      </div>
      <div class="p-3 flex justify-between border-t border-default mt-2">
        <RuiButton
          variant="text"
          color="primary"
          :disabled="allNotifications.length === 0"
          @click="showConfirmation()"
        >
          {{ t('notification_sidebar.clear_tooltip') }}
        </RuiButton>
        <RouterLink :to="Routes.CALENDAR">
          <RuiButton
            color="primary"
            @click="close()"
          >
            <template #prepend>
              <RuiIcon
                name="calendar-event-line"
                size="20"
              />
            </template>
            {{ t('notification_sidebar.view_calendar') }}
          </RuiButton>
        </RouterLink>
      </div>
    </div>
  </VNavigationDrawer>
</template>

<style module lang="scss">
.sidebar {
  @apply pt-0 top-[4rem] #{!important};
  box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);
  border-top: var(--v-rotki-light-grey-darken1) solid thin;
}

.mobile {
  @apply pt-0 top-[3.5rem] #{!important};
}

.no-messages {
  @apply flex flex-col items-center justify-center flex-1;
}

.messages {
  @apply flex flex-col;
  height: calc(100% - 133px);
}

.content {
  @apply ps-3.5 flex-1;
}
</style>
