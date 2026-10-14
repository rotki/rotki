<script setup lang="ts">
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <HintMenuIcon>
    <div class="flex flex-col gap-2 text-sm">
      <p class="m-0">
        <span class="font-medium">{{ t('address_book.hint.global') }}</span>
        {{ t('address_book.hint.global_description') }}
      </p>
      <p class="m-0">
        <span class="font-medium">{{ t('address_book.hint.private') }}</span>
        {{ t('address_book.hint.private_description') }}
      </p>
    </div>
  </HintMenuIcon>
</template>
