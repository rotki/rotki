<script setup lang="ts">
import type { SuggestionSelection } from './use-settings-suggestions';
import { groupBy } from 'es-toolkit';
import { getSuggestionKey, type PendingSuggestion, type SuggestionAction } from './settings-suggestions';
import SettingsSuggestionItem from './SettingsSuggestionItem.vue';

const modelValue = defineModel<boolean>({ required: true });

const { suggestions } = defineProps<{
  suggestions: readonly PendingSuggestion[];
}>();

const emit = defineEmits<{
  apply: [selection: SuggestionSelection];
  dismiss: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const acceptedKeys = ref<Set<string>>(new Set());
const selectedChoices = ref<Record<string, string>>({});

function defaultChoiceOf(suggestion: PendingSuggestion): string | undefined {
  const choices = suggestion.choices;
  if (!choices || choices.length === 0)
    return undefined;

  return suggestion.recommendedChoice ?? choices[0].id;
}

watch(
  () => suggestions,
  (items) => {
    set(acceptedKeys, new Set(items.map(s => getSuggestionKey(s))));
    set(selectedChoices, Object.fromEntries(
      items.flatMap((s) => {
        const choice = defaultChoiceOf(s);
        return choice ? [[getSuggestionKey(s), choice]] : [];
      }),
    ));
  },
  { immediate: true },
);

function isAccepted(suggestion: PendingSuggestion): boolean {
  return get(acceptedKeys).has(getSuggestionKey(suggestion));
}

function choiceOf(suggestion: PendingSuggestion): string | undefined {
  return get(selectedChoices)[getSuggestionKey(suggestion)];
}

function selectChoice(suggestion: PendingSuggestion, choice: string): void {
  set(selectedChoices, { ...get(selectedChoices), [getSuggestionKey(suggestion)]: choice });
}

/**
 * The dialog closes without marking the version applied, so it comes back at the next login until
 * the user has actually decided — which is what they are being sent away to make possible.
 */
function runAction(action: SuggestionAction): void {
  set(modelValue, false);
  router.push({ name: '/api-keys/external/', query: { service: action.service } });
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
  emit('apply', {
    choices: get(selectedChoices),
    selected: suggestions.filter(s => isAccepted(s)),
  });
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
            :choice="choiceOf(item)"
            @toggle="toggleAccepted(item)"
            @select="selectChoice(item, $event)"
            @action="runAction($event)"
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
          data-testid="apply-suggestions"
          @click="apply()"
        >
          {{ t("settings_suggestions.apply_selected") }}
        </RuiButton>
      </div>
    </RuiCard>
  </RuiDialog>
</template>
