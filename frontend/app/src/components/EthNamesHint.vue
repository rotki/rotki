<script setup lang="ts">
const { t } = useI18n();

const visible = ref(false);
</script>

<template>
  <div>
    <RuiButton id="eth-names-hint" variant="text" icon @click="visible = true">
      <RuiIcon name="question-line" />
    </RuiButton>
    <VMenu v-model="visible" offset-x nudge-right="25" attach="#eth-names-hint">
      <div class="pa-4 min-w-[20rem] flex flex-col gap-2">
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
