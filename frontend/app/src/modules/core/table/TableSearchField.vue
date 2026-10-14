<script setup lang="ts">
/** A table toolbar's search: on the right, as the dashboard's tables keep theirs, at the filter bar's height. */
const search = defineModel<string>({ required: true });

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTextField
    v-model="search"
    color="primary"
    dense
    prepend-icon="lu-search"
    :placeholder="t('common.actions.search')"
    :aria-label="t('common.actions.search')"
    class="ml-auto w-full max-w-64 [&_input]:py-1.5! [&_input]:text-sm! [&_input]:leading-5! [&_input::placeholder]:opacity-100! [&_input::placeholder]:text-rui-text-secondary! [&_svg]:size-4!"
    hide-details
    clearable
    @click:clear="search = ''"
  />
</template>
