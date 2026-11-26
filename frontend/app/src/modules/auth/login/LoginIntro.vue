<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { useI18n } from 'vue-i18n';
import LoginNotices from '@/modules/auth/login/LoginNotices.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <h1 class="text-h4 mb-2">
    {{ t('login.title') }}
  </h1>

  <div class="text-body-1 text-rui-text-secondary mb-8">
    <i18n-t
      scope="global"
      keypath="login.description.intro"
      tag="p"
    >
      <template #documentation>
        <ExternalLink
          :text="t('login.description.learn_more')"
          :url="externalLinks.usageGuide"
        />
      </template>
    </i18n-t>
  </div>

  <LoginNotices />
</template>
