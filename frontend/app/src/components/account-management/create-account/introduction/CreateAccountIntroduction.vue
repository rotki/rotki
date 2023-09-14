<script lang="ts" setup>
const emit = defineEmits<{
  (e: 'next'): void;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-8">
    <i18n
      path="create_account.introduction.description"
      class="text-center text-rui-text-secondary whitespace-break-spaces"
      tag="div"
    >
      <template #highlight>
        <strong>{{ t('create_account.introduction.highlight') }}</strong>
      </template>
    </i18n>
    <RuiButton
      size="lg"
      class="w-full"
      color="primary"
      data-cy="create-account__introduction__continue"
      @click="emit('next')"
    >
      {{ t('common.actions.continue') }}
    </RuiButton>
  </div>
</template>
