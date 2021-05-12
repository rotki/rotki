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
    <v-row justify="space-between" class="mt-2 pa-4">
      <v-col class="text-h5">{{ $t('help_sidebar.title') }}</v-col>
      <v-col cols="auto">
        <v-btn icon @click="visibleUpdate(false)">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-col>
    </v-row>
    <v-list class="mt-4">
      <v-list-item
        v-for="(item, index) in entries"
        :key="index"
        :href="$interop.isPackaged ? null : item.link"
        target="_blank"
        @click="$interop.isPackaged ? $interop.openUrl(item.link) : null"
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
      <v-list-item v-if="!$interop.isPackaged" selectable @click="openAbout()">
        <v-list-item-avatar>
          <v-icon>mdi-information</v-icon>
        </v-list-item-avatar>
        <v-list-item-content>
          <v-list-item-title>{{ $t('help_sidebar.about') }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ $t('help_sidebar.about_subtitle') }}
          </v-list-item-subtitle>
        </v-list-item-content>
        <v-list-item-action>
          <v-icon>mdi-chevron-right</v-icon>
        </v-list-item-action>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

type Entry = {
  readonly icon: string;
  readonly title: string;
  readonly subtitle: string;
  readonly link: string;
};

@Component({
  name: 'HelpSidebar'
})
export default class HelpSidebar extends Vue {
  @Prop({ required: true, type: Boolean })
  visible!: boolean;

  @Emit('visible:update')
  visibleUpdate(_visible: boolean) {}

  @Emit('about')
  openAbout() {
    this.visibleUpdate(false);
  }

  readonly entries: Entry[] = [
    {
      icon: 'mdi-book-open-page-variant',
      title: this.$t('help_sidebar.user_guide.title').toString(),
      subtitle: this.$t('help_sidebar.user_guide.subtitle').toString(),
      link: 'https://rotki.readthedocs.io/en/latest/usage_guide.html'
    },
    {
      icon: 'mdi-frequently-asked-questions',
      title: this.$t('help_sidebar.faq.title').toString(),
      subtitle: this.$t('help_sidebar.faq.subtitle').toString(),
      link: 'https://rotki.readthedocs.io/en/latest/faq.html'
    },
    {
      icon: 'mdi-discord',
      title: this.$t('help_sidebar.support.title').toString(),
      subtitle: this.$t('help_sidebar.support.subtitle').toString(),
      link: 'https://discord.gg/aGCxHG7'
    },
    {
      icon: 'mdi-github',
      title: this.$t('help_sidebar.github.title').toString(),
      subtitle: this.$t('help_sidebar.github.subtitle').toString(),
      link: 'https://github.com/rotki/rotki'
    },
    {
      icon: 'mdi-twitter',
      title: this.$t('help_sidebar.twitter.title').toString(),
      subtitle: this.$t('help_sidebar.twitter.subtitle').toString(),
      link: 'https://twitter.com/rotkiapp'
    }
  ];
}
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
