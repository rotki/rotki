<script setup lang="ts">
const { t } = useI18n();

const visible = ref(false);
</script>

<template>
  <div>
    <VMenu
      v-model="visible"
      offset-x
    >
      <template #activator="{ props }">
        <RuiButton
          variant="text"
          icon
          v-bind="props"
          @click="visible = true"
        >
          <RuiIcon name="question-line" />
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
    </VMenu>
  </div>
</template>
