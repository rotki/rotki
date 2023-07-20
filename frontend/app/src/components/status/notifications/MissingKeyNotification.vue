<script setup lang="ts">
import { type I18nParam } from '@rotki/common/lib/messages';

defineProps<{
  params: I18nParam;
}>();
</script>

<template>
  <i18n :path="params.message" :plural="params.choice" tag="div">
    <template #service>
      {{ params.props.service }}
    </template>
    <template #location>
      {{ params.props.location }}
    </template>
    <template #url>
      <BaseExternalLink :href="params.props.url" :text="params.props.url" />
    </template>
  </i18n>
</template>
