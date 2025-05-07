<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
    <RuiMenu :popper="{ placement: 'right' }">
      <template #activator="{ attrs }">
        <RuiButton
          variant="text"
          icon
          v-bind="attrs"
        >
          <RuiIcon name="lu-circle-help" />
        </RuiButton>
      </template>
      <div class="p-4 max-w-[20rem] flex flex-col gap-2">
        <div>
          <b>{{ t('address_book.hint.global') }}</b>
          {{ t('address_book.hint.global_description') }}
        </div>
        <div>
          <b>{{ t('address_book.hint.private') }}</b>
          {{ t('address_book.hint.private_description') }}
        </div>
      </div>
    </RuiMenu>
  </div>
</template>
