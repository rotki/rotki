<script setup lang="ts">
import { IndexedDb } from '@/utils/indexed-db';
import { TWITTER_URL, externalLinks } from '@/data/external-links';
import type { RuiIcons } from '@rotki/ui-library';

const emit = defineEmits<{
  (e: 'about'): void;
}>();

const { t } = useI18n();

const display = defineModel<boolean>({ required: true });

interface Entry {
  readonly icon: RuiIcons;
  readonly title: string;
  readonly subtitle: string;
  readonly link: string;
}

const entries: Entry[] = [
  {
    icon: 'book-open-line',
    title: t('help_sidebar.user_guide.title'),
    subtitle: t('help_sidebar.user_guide.subtitle'),
    link: externalLinks.usageGuide,
  },
  {
    icon: 'questionnaire-line',
    title: t('help_sidebar.faq.title'),
    subtitle: t('help_sidebar.faq.subtitle'),
    link: externalLinks.faq,
  },
  {
    icon: 'discord-line',
    title: t('help_sidebar.support.title'),
    subtitle: t('help_sidebar.support.subtitle'),
    link: externalLinks.discord,
  },
  {
    icon: 'github-line',
    title: t('help_sidebar.github.title'),
    subtitle: t('help_sidebar.github.subtitle'),
    link: externalLinks.github,
  },
  {
    icon: 'twitter-x-line',
    title: t('help_sidebar.twitter.title'),
    subtitle: t('help_sidebar.twitter.subtitle'),
    link: TWITTER_URL,
  },
];

const interop = useInterop();

function openAbout() {
  set(display, false);
  emit('about');
}

async function downloadBrowserLog() {
  const loggerDb = new IndexedDb('db', 1, 'logs');

  await loggerDb.getAll((data: any) => {
    if (data?.length === 0) {
      const { notify } = useNotificationsStore();
      notify({
        title: t('help_sidebar.browser_log.error.empty.title'),
        message: t('help_sidebar.browser_log.error.empty.message'),
        display: true,
      });
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
    width="400px"
    temporary
    position="right"
  >
    <div class="flex justify-between items-center p-2 pl-4">
      <div class="text-h6">
        {{ t('help_sidebar.title') }}
      </div>
      <RuiButton
        variant="text"
        icon
        @click="display = false"
      >
        <RuiIcon name="close-line" />
      </RuiButton>
    </div>
    <div class="py-0">
      <a
        v-for="(item, index) in entries"
        :key="index"
        :href="interop.isPackaged ? undefined : item.link"
        target="_blank"
        class="flex items-center gap-6 py-4 px-6 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800 cursor-pointer"
        :class="{ 'border-t border-default': index > 0 }"
        @click="interop.isPackaged ? interop.openUrl(item.link) : null"
      >
        <RuiIcon
          class="text-rui-text-secondary"
          :name="item.icon"
        />

        <div class="gap-1">
          <div class="text-rui-text font-medium">{{ item.title }}</div>
          <div class="text-rui-text-secondary text-caption">
            {{ item.subtitle }}
          </div>
        </div>
      </a>
      <template v-if="!interop.isPackaged">
        <div
          class="flex items-center gap-6 py-4 px-6 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800 border-t border-default cursor-pointer"
          @click="openAbout()"
        >
          <RuiIcon
            class="text-rui-text-secondary"
            name="information-line"
          />

          <div class="gap-1">
            <div class="text-rui-text font-medium">
              {{ t('help_sidebar.about.title') }}
            </div>
            <div class="text-rui-text-secondary text-caption">
              {{ t('help_sidebar.about.subtitle') }}
            </div>
          </div>
        </div>

        <div
          class="flex items-center gap-6 py-4 px-6 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800 border-t border-default cursor-pointer"
          @click="downloadBrowserLog()"
        >
          <RuiIcon
            class="text-rui-text-secondary"
            name="file-download-line"
          />

          <div class="gap-1">
            <div class="text-rui-text font-medium">
              {{ t('help_sidebar.browser_log.title') }}
            </div>
            <div class="text-rui-text-secondary text-caption">
              {{ t('help_sidebar.browser_log.subtitle') }}
            </div>
          </div>
        </div>
      </template>
    </div>
  </RuiNavigationDrawer>
</template>
