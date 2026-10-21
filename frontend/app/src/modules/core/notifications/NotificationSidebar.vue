<script setup lang="ts">
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { NotificationDayLabel } from '@/modules/core/notifications/notification-days';
import Notification from '@/modules/core/notifications/Notification.vue';
import BackendProblemCard from '@/modules/core/notifications/problems/BackendProblemCard.vue';
import { useNotificationSidebar } from '@/modules/core/notifications/use-notification-sidebar';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import LazyLoader from '@/modules/shell/components/LazyLoader.vue';

const display = defineModel<boolean>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const contentWrapper = useTemplateRef<HTMLDivElement>('contentWrapper');
const { y } = useScroll(contentWrapper);

const { visible: dialogVisible } = storeToRefs(useConfirmStore());

const [DefineNoMessages, ReuseNoMessages] = createReusableTemplate();

const {
  close,
  failures,
  historyDays,
  initialAppear,
  isEmpty,
  messageOverflow,
  modelProblemsOpen,
  problems,
  remove,
  removeProblem,
  showConfirmation,
  silent,
  toggleSilentMode,
} = useNotificationSidebar({ display, scrollY: y });

const problemCount = computed<number>(() => get(problems).length + get(failures).length);
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
          {{ t('notification_sidebar.empty.title') }}
        </div>
        <div class="text-sm text-rui-text-secondary max-w-64">
          {{ t('notification_sidebar.empty.description') }}
        </div>
      </div>
    </DefineNoMessages>
    <div class="h-full overflow-hidden flex flex-col">
      <div class="flex shrink-0 justify-between items-center py-2 pl-4 pr-2">
        <div class="text-base font-semibold text-rui-text">
          {{ t('notification_sidebar.title') }}
        </div>
        <div class="flex items-center">
          <RuiTooltip :open-delay="400">
            <template #activator>
              <RuiButton
                variant="text"
                icon
                :color="silent ? 'primary' : undefined"
                :class="{ 'text-rui-text-secondary!': !silent }"
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
            class="text-rui-text-secondary!"
            :aria-label="t('common.actions.close')"
            data-testid="close-notifications"
            @click="close()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </div>

      <ReuseNoMessages v-if="isEmpty" />
      <div
        v-else
        ref="contentWrapper"
        class="flex flex-col flex-1 min-h-0 gap-2 ps-3.5 pe-2 pb-2 overflow-y-auto"
      >
        <template
          v-for="day in historyDays"
          :key="day.key"
        >
          <div
            class="sticky top-0 z-1 bg-rui-surface pt-2 pb-0.5 text-caption font-medium text-rui-text-secondary"
            data-testid="notification-day"
          >
            <template v-if="day.label === NotificationDayLabel.TODAY">
              {{ t('notification_sidebar.day.today') }}
            </template>
            <template v-else-if="day.label === NotificationDayLabel.YESTERDAY">
              {{ t('notification_sidebar.day.yesterday') }}
            </template>
            <DateDisplay
              v-else
              :timestamp="day.date.getTime()"
              milliseconds
              no-time
            />
          </div>
          <LazyLoader
            v-for="item in day.notifications"
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
        </template>

        <section
          v-if="problemCount > 0"
          class="flex flex-col gap-2"
          data-testid="notification-problems"
        >
          <button
            type="button"
            class="sticky top-0 z-1 bg-rui-surface pt-2 pb-0.5 flex items-center gap-1.5 text-caption font-medium text-rui-text-secondary cursor-pointer"
            :aria-expanded="modelProblemsOpen"
            data-testid="notification-problems-toggle"
            @click="modelProblemsOpen = !modelProblemsOpen"
          >
            {{ t('notification_sidebar.problems', { count: problemCount }) }}
            <RuiIcon
              size="16"
              :name="modelProblemsOpen ? 'lu-chevron-up' : 'lu-chevron-down'"
            />
          </button>
          <template v-if="modelProblemsOpen">
            <BackendProblemCard
              v-for="problem in problems"
              :key="problem.id"
              class="grow-0 shrink-0"
              :problem="problem"
              @dismiss="removeProblem($event)"
              @acted="close()"
            />
            <LazyLoader
              v-for="item in failures"
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
          </template>
        </section>

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
      <div class="p-3 flex justify-end border-t border-rui-divider mt-2">
        <RuiButton
          v-if="!isEmpty"
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
