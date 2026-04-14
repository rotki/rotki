<script setup lang="ts">
import { groupBy } from 'es-toolkit';
import { getSuggestionKey, type PendingSuggestion } from './settings-suggestions';
import SettingsSuggestionItem from './SettingsSuggestionItem.vue';

const modelValue = defineModel<boolean>({ required: true });

const { suggestions } = defineProps<{
  suggestions: readonly PendingSuggestion[];
}>();

const emit = defineEmits<{
  apply: [selected: PendingSuggestion[]];
  dismiss: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const acceptedKeys = ref<Set<string>>(new Set());

watch(
  () => suggestions,
  (items) => {
    set(acceptedKeys, new Set(items.map(s => getSuggestionKey(s))));
  },
  { immediate: true },
);

function isAccepted(suggestion: PendingSuggestion): boolean {
  return get(acceptedKeys).has(getSuggestionKey(suggestion));
}

const grouped = computed<Record<string, PendingSuggestion[]>>(
  () => groupBy([...suggestions], s => s.fromVersion),
);

function toggleAccepted(suggestion: PendingSuggestion): void {
  const key = getSuggestionKey(suggestion);
  const keys = new Set(get(acceptedKeys));
  if (keys.has(key))
    keys.delete(key);
  else
    keys.add(key);
  set(acceptedKeys, keys);
}

function apply(): void {
  const selected = suggestions.filter(s => isAccepted(s));
  emit('apply', selected);
}

function dismiss(): void {
  emit('dismiss');
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="600"
  >
    <RuiCard divide>
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 py-2">
          <span class="text-h6 text-rui-text">
            {{ t("settings_suggestions.dialog.title") }}
          </span>
          <RuiButton
            variant="text"
            icon
            @click="modelValue = false"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </template>

      <div class="px-4 py-2 text-body-2 text-rui-text-secondary">
        {{ t("settings_suggestions.dialog.description") }}
      </div>

      <div class="px-4 py-2 max-h-[60vh] overflow-y-auto">
        <div
          v-for="(items, version) in grouped"
          :key="version"
          class="mb-4 last:mb-0"
        >
          <div class="text-subtitle-2 text-rui-text-secondary mb-2">
            {{ t("settings_suggestions.dialog.version_group", { version }) }}
          </div>

          <SettingsSuggestionItem
            v-for="item in items"
            :key="getSuggestionKey(item)"
            :suggestion="item"
            :accepted="isAccepted(item)"
            @toggle="toggleAccepted(item)"
          />
        </div>
      </div>

      <div class="flex justify-end gap-2 px-4 py-3">
        <RuiButton
          variant="text"
          color="primary"
          @click="dismiss()"
        >
          {{ t("settings_suggestions.keep_current") }}
        </RuiButton>
        <RuiButton
          color="primary"
          @click="apply()"
        >
          {{ t("settings_suggestions.apply_selected") }}
        </RuiButton>
      </div>
    </RuiCard>
  </RuiDialog>
</template>
