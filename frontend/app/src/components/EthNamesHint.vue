<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <VMenu offset-x nudge-right="8" max-width="400">
    <template #activator="{ on, attrs }">
      <VIcon v-bind="attrs" v-on="on"> mdi-help-circle</VIcon>
    </template>
    <div class="pa-4">
      <div class="pb-4">
        <div>
          <b>{{ t('address_book.hint.global') }}</b>
          {{ t('address_book.hint.global_description') }}
        </div>
        <div>
          <b>{{ t('address_book.hint.private') }}</b>
          {{ t('address_book.hint.private_description') }}
        </div>
      </div>
    </div>
  </VMenu>
</template>
