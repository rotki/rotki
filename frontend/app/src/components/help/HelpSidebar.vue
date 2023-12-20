<script setup lang="ts">
import IndexedDb from '@/utils/indexed-db';
import { TWITTER_URL, externalLinks } from '@/data/external-links';

defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: 'visible:update', visible: boolean): void;
  (e: 'about'): void;
}>();
const { t } = useI18n();

interface Entry {
  readonly icon: string;
  readonly title: string;
  readonly subtitle: string;
  readonly link: string;
}

const entries: Entry[] = [
  {
    icon: 'book-open-line',
    title: t('help_sidebar.user_guide.title').toString(),
    subtitle: t('help_sidebar.user_guide.subtitle').toString(),
    link: externalLinks.usageGuide
  },
  {
    icon: 'questionnaire-line',
    title: t('help_sidebar.faq.title').toString(),
    subtitle: t('help_sidebar.faq.subtitle').toString(),
    link: externalLinks.faq
  },
  {
    icon: 'discord-line',
    title: t('help_sidebar.support.title').toString(),
    subtitle: t('help_sidebar.support.subtitle').toString(),
    link: externalLinks.discord
  },
  {
    icon: 'github-line',
    title: t('help_sidebar.github.title').toString(),
    subtitle: t('help_sidebar.github.subtitle').toString(),
    link: externalLinks.github
  },
  {
    icon: 'twitter-x-line',
    title: t('help_sidebar.twitter.title').toString(),
    subtitle: t('help_sidebar.twitter.subtitle').toString(),
    link: TWITTER_URL
  }
];

const interop = useInterop();

const visibleUpdate = (_visible: boolean) => {
  emit('visible:update', _visible);
};

const openAbout = () => {
  visibleUpdate(false);
  emit('about');
};

const downloadBrowserLog = async () => {
  const loggerDb = new IndexedDb('db', 1, 'logs');

  await loggerDb.getAll((data: any) => {
    if (data?.length === 0) {
      const { notify } = useNotificationsStore();
      notify({
        title: t('help_sidebar.browser_log.error.empty.title').toString(),
        message: t('help_sidebar.browser_log.error.empty.message').toString(),
        display: true
      });
      return;
    }
    const messages = data.map((item: any) => item.message).join('\n');
    downloadFileByTextContent(messages, 'frontend_log.txt');
  });
};

const { smAndDown } = useDisplay();
</script>

<template>
  <VNavigationDrawer
    width="400px"
    class="help-sidebar"
    :class="smAndDown ? 'help-sidebar--mobile' : null"
    absolute
    clipped
    :value="visible"
    right
    temporary
    hide-overlay
    @input="visibleUpdate($event)"
  >
    <div class="flex justify-between items-center pa-4">
      <div class="text-h6">{{ t('help_sidebar.title') }}</div>
      <RuiButton variant="text" icon @click="visibleUpdate(false)">
        <RuiIcon name="close-line" />
      </RuiButton>
    </div>
    <div class="py-0">
      <a
        v-for="(item, index) in entries"
        :key="index"
        :href="interop.isPackaged ? undefined : item.link"
        target="_blank"
        class="flex items-center gap-6 py-4 px-6 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800"
        :class="{ 'border-t border-default': index > 0 }"
        @click="interop.isPackaged ? interop.openUrl(item.link) : null"
      >
        <RuiIcon class="text-rui-text-secondary" :name="item.icon" />

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
          <RuiIcon class="text-rui-text-secondary" name="information-line" />

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
          <RuiIcon class="text-rui-text-secondary" name="file-download-line" />

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
  </VNavigationDrawer>
</template>

<style scoped lang="scss">
.help-sidebar {
  top: 64px !important;
  box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);
  padding-top: 0 !important;
  border-top: var(--v-rotki-light-grey-darken1) solid thin;

  &--mobile {
    top: 56px !important;
  }

  &.v-navigation-drawer {
    &--is-mobile {
      padding-top: 0 !important;
    }
  }
}
</style>
