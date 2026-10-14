<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import { Priority, Severity } from '@rotki/common';
import { externalLinks, TWITTER_URL } from '@shared/external-links';
import { downloadFileByTextContent } from '@/modules/core/common/file/download';
import { IndexedDb } from '@/modules/core/common/helpers/indexed-db';
import { useReportIssue } from '@/modules/core/common/use-report-issue';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const display = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  about: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const interop = useInterop();

const { show: showReportIssue } = useReportIssue();
const { notify } = useNotificationDispatcher();

interface Entry {
  readonly icon: RuiIcons;
  readonly title: string;
  readonly subtitle: string;
  readonly link: string;
  /** Marks the row as leaving the app; reusable-template props take no boolean shorthand. */
  readonly external: true;
}

/** Where to read up or ask: shown first, since that is what most visits are for. */
const helpLinks: Entry[] = [
  {
    external: true,
    icon: 'lu-book-open',
    link: externalLinks.usageGuide,
    subtitle: t('help_sidebar.user_guide.subtitle'),
    title: t('help_sidebar.user_guide.title'),
  },
  {
    external: true,
    icon: 'lu-message-circle-question-mark',
    link: externalLinks.faq,
    subtitle: t('help_sidebar.faq.subtitle'),
    title: t('help_sidebar.faq.title'),
  },
  {
    external: true,
    icon: 'lu-discord',
    link: externalLinks.discord,
    subtitle: t('help_sidebar.support.subtitle'),
    title: t('help_sidebar.support.title'),
  },
];

const projectLinks: Entry[] = [
  {
    external: true,
    icon: 'lu-github',
    link: externalLinks.github,
    subtitle: t('help_sidebar.github.subtitle'),
    title: t('help_sidebar.github.title'),
  },
  {
    external: true,
    icon: 'lu-x-twitter',
    link: TWITTER_URL,
    subtitle: t('help_sidebar.twitter.subtitle'),
    title: t('help_sidebar.twitter.title'),
  },
];

const [DefineRow, ReuseRow] = createReusableTemplate<{
  icon: RuiIcons;
  title: string;
  subtitle: string;
  external?: boolean;
}>();

const rowClass = 'group flex w-full items-center gap-3 rounded-rui-control px-2 py-2 text-left transition-colors hover:bg-rui-grey-100 focus-visible:outline-2 focus-visible:outline-rui-primary dark:hover:bg-rui-grey-800';

function openAbout(): void {
  set(display, false);
  emit('about');
}

async function downloadBrowserLog(): Promise<void> {
  const loggerDb = new IndexedDb('db', 1, 'logs');

  await loggerDb.getAll((data: any) => {
    if (data?.length === 0) {
      notify({ message: t('help_sidebar.browser_log.error.empty.message'), priority: Priority.HIGH, severity: Severity.WARNING, title: t('help_sidebar.browser_log.error.empty.title') });
      return;
    }
    const messages = data.map((item: any) => item.message).join('\n');
    downloadFileByTextContent(messages, 'frontend_log.txt');
  });
}
</script>

<template>
  <RuiNavigationDrawer
    v-model="display"
    below-app-bar
    width="400px"
    temporary
    position="right"
    class="flex flex-col"
    :class-names="{ content: 'flex flex-col' }"
  >
    <DefineRow #default="{ icon, title, subtitle, external }">
      <span class="flex size-8 shrink-0 items-center justify-center rounded-rui-control bg-rui-grey-100 text-rui-text-secondary transition-colors group-hover:bg-rui-grey-200 dark:bg-rui-grey-800 dark:group-hover:bg-rui-grey-700">
        <RuiIcon
          :name="icon"
          size="16"
        />
      </span>
      <span class="flex min-w-0 flex-1 flex-col">
        <span class="text-sm font-medium text-rui-text">{{ title }}</span>
        <span class="text-xs text-rui-text-secondary">{{ subtitle }}</span>
      </span>
      <RuiIcon
        v-if="external"
        name="lu-arrow-up-right"
        size="14"
        class="shrink-0 text-rui-text-disabled transition-colors group-hover:text-rui-text-secondary"
      />
    </DefineRow>

    <div class="flex shrink-0 items-center justify-between border-b border-rui-divider py-2 pl-4 pr-2">
      <div class="text-base font-semibold text-rui-text">
        {{ t('help_sidebar.title') }}
      </div>
      <RuiButton
        variant="text"
        icon
        class="text-rui-text-secondary!"
        :aria-label="t('common.actions.close')"
        data-testid="help-close"
        @click="display = false"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>
    <div class="flex min-h-0 grow flex-col gap-4 overflow-y-auto p-2 pb-4">
      <section class="flex flex-col">
        <div class="px-2 pb-1 pt-2 text-xs font-medium text-rui-text-secondary">
          {{ t('help_sidebar.sections.get_help') }}
        </div>
        <a
          v-for="item in helpLinks"
          :key="item.link"
          :href="interop.isPackaged ? undefined : item.link"
          target="_blank"
          :class="rowClass"
          data-testid="help-link"
          @click="interop.isPackaged ? interop.openUrl(item.link) : null"
        >
          <ReuseRow v-bind="item" />
        </a>
      </section>

      <section class="flex flex-col">
        <div class="px-2 pb-1 pt-2 text-xs font-medium text-rui-text-secondary">
          {{ t('help_sidebar.sections.report') }}
        </div>
        <button
          type="button"
          :class="rowClass"
          data-testid="help-report-issue"
          @click="showReportIssue()"
        >
          <ReuseRow
            icon="lu-bug"
            :title="t('help_sidebar.report_issue.title')"
            :subtitle="t('help_sidebar.report_issue.subtitle')"
          />
        </button>
        <button
          v-if="!interop.isPackaged"
          type="button"
          :class="rowClass"
          data-testid="help-download-log"
          @click="downloadBrowserLog()"
        >
          <ReuseRow
            icon="lu-file-down"
            :title="t('help_sidebar.browser_log.title')"
            :subtitle="t('help_sidebar.browser_log.subtitle')"
          />
        </button>
      </section>

      <section class="flex flex-col">
        <div class="px-2 pb-1 pt-2 text-xs font-medium text-rui-text-secondary">
          {{ t('help_sidebar.sections.more') }}
        </div>
        <a
          v-for="item in projectLinks"
          :key="item.link"
          :href="interop.isPackaged ? undefined : item.link"
          target="_blank"
          :class="rowClass"
          data-testid="help-link"
          @click="interop.isPackaged ? interop.openUrl(item.link) : null"
        >
          <ReuseRow v-bind="item" />
        </a>
        <button
          v-if="!interop.isPackaged"
          type="button"
          :class="rowClass"
          data-testid="help-about"
          @click="openAbout()"
        >
          <ReuseRow
            icon="lu-info"
            :title="t('help_sidebar.about.title')"
            :subtitle="t('help_sidebar.about.subtitle')"
          />
        </button>
      </section>
    </div>
  </RuiNavigationDrawer>
</template>
