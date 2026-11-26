<script setup lang="ts">
import SettingsSuggestionsDialog from '@/modules/settings/suggestions/SettingsSuggestionsDialog.vue';
import { useSettingsSuggestions } from '@/modules/settings/suggestions/use-settings-suggestions';
import { useSuggestionsStore } from '@/modules/settings/suggestions/use-suggestions-store';

const { applySelected, dismissAll } = useSettingsSuggestions();
const suggestionsStore = useSuggestionsStore();
</script>

<template>
  <SettingsSuggestionsDialog
    v-model="suggestionsStore.showSuggestionsDialog"
    :suggestions="suggestionsStore.pendingSuggestions"
    @apply="applySelected($event)"
    @dismiss="dismissAll()"
  />
</template>
