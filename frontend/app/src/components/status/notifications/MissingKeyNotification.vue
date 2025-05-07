<script setup lang="ts">
import type { I18nParam } from '@rotki/common';
import ExternalLink from '@/components/helper/ExternalLink.vue';

defineProps<{
  params: I18nParam;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <i18n-t
    scope="global"
    :keypath="params.message"
    :plural="params.choice"
    tag="div"
  >
    <template #service>
      {{ params.props.service }}
    </template>
    <template #location>
      {{ params.props.location }}
    </template>
    <template #docs>
      <ExternalLink
        v-if="params.props.docsUrl"
        class="leading-4"
        :url="params.props.docsUrl"
        color="primary"
      >
        {{ t('common.here') }}
      </ExternalLink>
    </template>
  </i18n-t>
</template>
