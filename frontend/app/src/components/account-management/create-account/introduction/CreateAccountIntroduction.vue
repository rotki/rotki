<script lang="ts" setup>
const emit = defineEmits<{
  (e: 'next'): void;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="space-y-8">
    <i18n-t
      scope="global"
      keypath="create_account.introduction.description"
      class="text-center text-rui-text-secondary whitespace-break-spaces"
      tag="div"
    >
      <template #highlight>
        <strong>{{ t('create_account.introduction.highlight') }}</strong>
      </template>
    </i18n-t>
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
