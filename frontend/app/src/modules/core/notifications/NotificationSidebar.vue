<script setup lang="ts">
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import Notification from '@/modules/core/notifications/Notification.vue';
import { TAB_ORDER, TabCategory, useNotificationSidebar } from '@/modules/core/notifications/use-notification-sidebar';
import LazyLoader from '@/modules/shell/components/LazyLoader.vue';

const display = defineModel<boolean>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const contentWrapper = useTemplateRef<HTMLDivElement>('contentWrapper');
const { y } = useScroll(contentWrapper);

const { visible: dialogVisible } = storeToRefs(useConfirmStore());

const [DefineNoMessages, ReuseNoMessages] = createReusableTemplate();

const {
  allNotifications,
  close,
  initialAppear,
  messageOverflow,
  modelSelectedTab,
  remove,
  selectedNotifications,
  showConfirmation,
  silent,
  tabCategoriesLabel,
  toggleSilentMode,
} = useNotificationSidebar({ display, scrollY: y });

/** Nothing at all reads as caught up; an empty filter names what it filters and points back to All. */
const emptyState = computed<{ title: string; description: string }>(() => {
  if (get(allNotifications).length === 0)
    return { description: t('notification_sidebar.empty.description'), title: t('notification_sidebar.empty.title') };

  const title = get(modelSelectedTab) === TabCategory.ERROR
    ? t('notification_sidebar.empty_tab.error')
    : t('notification_sidebar.empty_tab.reminder');
  return { description: t('notification_sidebar.empty_tab.description'), title };
});
</script>

<template>
  <RuiNavigationDrawer
    v-model="display"
    below-app-bar
    width="400px"
    position="right"
    temporary
    :stateless="dialogVisible"
  >
    <DefineNoMessages>
      <div
        class="flex flex-col items-center justify-center text-center gap-2 flex-1 px-8"
        data-testid="notifications-empty"
      >
        <div class="size-12 mb-2 rounded-full bg-rui-primary-soft flex items-center justify-center">
          <RuiIcon
            size="24"
            class="text-rui-primary"
            name="lu-bell-check"
          />
        </div>
        <div class="text-base font-medium text-rui-text">
          {{ emptyState.title }}
        </div>
        <div class="text-sm text-rui-text-secondary max-w-64">
          {{ emptyState.description }}
        </div>
      </div>
    </DefineNoMessages>
    <div class="h-full overflow-hidden flex flex-col">
      <div class="flex justify-between items-center p-2 pl-4">
        <div class="text-h6">
          {{ t('notification_sidebar.title') }}
        </div>
        <div class="flex items-center">
          <RuiTooltip :open-delay="400">
            <template #activator>
              <RuiButton
                variant="text"
                icon
                :color="silent ? 'primary' : undefined"
                data-testid="silent-notifications-toggle"
                @click="toggleSilentMode()"
              >
                <RuiIcon :name="silent ? 'lu-bell-off' : 'lu-bell'" />
              </RuiButton>
            </template>
            {{ silent ? t('notification_sidebar.silent.on') : t('notification_sidebar.silent.off') }}
          </RuiTooltip>
          <RuiButton
            variant="text"
            icon
            data-testid="close-notifications"
            @click="close()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </div>

      <ReuseNoMessages v-if="allNotifications.length === 0" />
      <div
        v-else
        class="flex flex-col flex-1 min-h-0"
      >
        <div class="border-b border-default mx-4">
          <RuiTabs
            v-model="modelSelectedTab"
            color="primary"
          >
            <RuiTab
              v-for="item in TAB_ORDER"
              :key="item"
              size="sm"
              class="min-w-0!"
              :value="item"
            >
              {{ tabCategoriesLabel[item] }}
            </RuiTab>
          </RuiTabs>
        </div>
        <div
          v-if="selectedNotifications.length > 0"
          ref="contentWrapper"
          class="ps-3.5 pe-2 mt-2 flex flex-col gap-2 overflow-y-auto!"
        >
          <LazyLoader
            v-for="item in selectedNotifications"
            :key="item.id"
            :initial-appear="initialAppear"
            min-height="120px"
            class="grow-0 shrink-0"
          >
            <Notification
              :notification="item"
              @dismiss="remove($event)"
            />
          </LazyLoader>
          <div
            v-if="messageOverflow"
            class="flex bg-rui-warning/10 rounded-md border p-2 gap-4"
          >
            <div class="flex flex-col justify-center items-center">
              <div class="rounded-full p-2 bg-rui-warning">
                <RuiIcon
                  size="20"
                  class="text-white"
                  name="lu-siren"
                />
              </div>
            </div>

            <div class="text-rui-text-secondary text-body-2 break-words">
              {{ t('notification_sidebar.message_overflow') }}
            </div>
          </div>
        </div>
        <ReuseNoMessages v-else />
      </div>
      <div class="p-3 flex justify-end border-t border-rui-divider mt-2">
        <RuiButton
          v-if="allNotifications.length > 0"
          variant="text"
          color="primary"
          class="me-auto"
          data-testid="clear-notifications"
          @click="showConfirmation()"
        >
          {{ t('notification_sidebar.clear_tooltip') }}
        </RuiButton>
        <RouterLink :to="{ name: '/calendar/' }">
          <RuiButton
            variant="outlined"
            color="primary"
            @click="close()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-calendar-days"
                size="20"
              />
            </template>
            {{ t('notification_sidebar.view_calendar') }}
          </RuiButton>
        </RouterLink>
      </div>
    </div>
  </RuiNavigationDrawer>
</template>
