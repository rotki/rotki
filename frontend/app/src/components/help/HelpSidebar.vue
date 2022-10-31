<template>
  <v-navigation-drawer
    width="400px"
    class="help-sidebar"
    :class="$vuetify.breakpoint.smAndDown ? 'help-sidebar--mobile' : null"
    absolute
    clipped
    :value="visible"
    right
    temporary
    hide-overlay
    @input="visibleUpdate($event)"
  >
    <v-row justify="space-between" class="mt-0 pa-4">
      <v-col class="text-h5">{{ t('help_sidebar.title') }}</v-col>
      <v-col cols="auto">
        <v-btn icon @click="visibleUpdate(false)">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-col>
    </v-row>
    <v-list class="mt-2">
      <v-list-item
        v-for="(item, index) in entries"
        :key="index"
        :href="interop.isPackaged ? null : item.link"
        target="_blank"
        @click="interop.isPackaged ? interop.openUrl(item.link) : null"
      >
        <v-list-item-avatar>
          <v-icon>{{ item.icon }}</v-icon>
        </v-list-item-avatar>
        <v-list-item-content>
          <v-list-item-title>
            {{ item.title }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ item.subtitle }}
          </v-list-item-subtitle>
        </v-list-item-content>
        <v-list-item-action>
          <v-icon>mdi-chevron-right</v-icon>
        </v-list-item-action>
      </v-list-item>
      <template v-if="!interop.isPackaged">
        <v-list-item selectable @click="openAbout()">
          <v-list-item-avatar>
            <v-icon>mdi-information</v-icon>
          </v-list-item-avatar>
          <v-list-item-content>
            <v-list-item-title>
              {{ t('help_sidebar.about.title') }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ t('help_sidebar.about.subtitle') }}
            </v-list-item-subtitle>
          </v-list-item-content>
          <v-list-item-action>
            <v-icon>mdi-chevron-right</v-icon>
          </v-list-item-action>
        </v-list-item>
        <v-list-item selectable @click="downloadBrowserLog()">
          <v-list-item-avatar>
            <v-icon>mdi-note-text</v-icon>
          </v-list-item-avatar>
          <v-list-item-content>
            <v-list-item-title>
              {{ t('help_sidebar.browser_log.title') }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ t('help_sidebar.browser_log.subtitle') }}
            </v-list-item-subtitle>
          </v-list-item-content>
          <v-list-item-action>
            <v-icon>mdi-chevron-right</v-icon>
          </v-list-item-action>
        </v-list-item>
      </template>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { interop } from '@/electron-interop';
import { useNotifications } from '@/store/notifications';
import { downloadFileByUrl } from '@/utils/download';
import IndexedDb from '@/utils/indexed-db';

const { t } = useI18n();
type Entry = {
  readonly icon: string;
  readonly title: string;
  readonly subtitle: string;
  readonly link: string;
};

const entries: Entry[] = [
  {
    icon: 'mdi-book-open-page-variant',
    title: t('help_sidebar.user_guide.title').toString(),
    subtitle: t('help_sidebar.user_guide.subtitle').toString(),
    link: 'https://rotki.readthedocs.io/en/latest/usage_guide.html'
  },
  {
    icon: 'mdi-frequently-asked-questions',
    title: t('help_sidebar.faq.title').toString(),
    subtitle: t('help_sidebar.faq.subtitle').toString(),
    link: 'https://rotki.readthedocs.io/en/latest/faq.html'
  },
  {
    icon: '$discord',
    title: t('help_sidebar.support.title').toString(),
    subtitle: t('help_sidebar.support.subtitle').toString(),
    link: 'https://discord.gg/aGCxHG7'
  },
  {
    icon: 'mdi-github',
    title: t('help_sidebar.github.title').toString(),
    subtitle: t('help_sidebar.github.subtitle').toString(),
    link: 'https://github.com/rotki/rotki'
  },
  {
    icon: 'mdi-twitter',
    title: t('help_sidebar.twitter.title').toString(),
    subtitle: t('help_sidebar.twitter.subtitle').toString(),
    link: 'https://twitter.com/rotkiapp'
  }
];

defineProps({
  visible: { required: true, type: Boolean }
});

const emit = defineEmits(['visible:update', 'about']);

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
      const { notify } = useNotifications();
      notify({
        title: t('help_sidebar.browser_log.error.empty.title').toString(),
        message: t('help_sidebar.browser_log.error.empty.message').toString(),
        display: true
      });
      return;
    }
    const messages = data.map((item: any) => item.message).join('\n');

    downloadFileByUrl(
      'data:text/plain;charset=utf-8,' + encodeURIComponent(messages),
      'frontend_log.txt'
    );
  });
};
</script>

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
