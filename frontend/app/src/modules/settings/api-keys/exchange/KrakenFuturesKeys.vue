<script setup lang="ts">
import { RuiRevealableTextField, RuiTextField } from '@rotki/ui-library';

/**
 * Kraken carries a second pair of credentials for its futures API. They are optional, but only
 * together, and like the main pair they are shown masked until the user asks to replace them —
 * the app never held the saved secret, so there is nothing behind the asterisks to reveal.
 */
const apiKey = defineModel<string | undefined>('apiKey', { required: true });
const apiSecret = defineModel<string | undefined>('apiSecret', { required: true });
/** Owned by the parent because the rules have to know whether a replacement is under way. */
const editing = defineModel<boolean>('editing', { required: true });

const { editMode = false, keyErrors = [], secretErrors = [] } = defineProps<{
  editMode?: boolean;
  keyErrors?: string[];
  secretErrors?: string[];
}>();

const { t } = useI18n({ useScope: 'global' });

const ASTERISKS = '*'.repeat(30);

const masked = computed<boolean>(() => editMode && !get(editing));

const inputComponent = computed(() => get(masked) ? RuiTextField : RuiRevealableTextField);

function maskedModel(model: Ref<string | undefined>): WritableComputedRef<string> {
  return computed<string>({
    get: () => get(masked) ? ASTERISKS : (get(model) ?? ''),
    set: value => set(model, value),
  });
}

const keyModel = maskedModel(apiKey);
const secretModel = maskedModel(apiSecret);

/** Abandoning the replacement must not leave a half typed pair behind to be saved. */
function toggle(): void {
  const next = !get(editing);
  set(editing, next);

  if (!next) {
    set(apiKey, '');
    set(apiSecret, '');
  }
}
</script>

<template>
  <div class="flex items-center gap-2 text-subtitle-2 pb-4">
    {{ t('exchange_settings.inputs.kraken_futures_keys') }}
    <RuiTooltip
      v-if="editMode"
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          data-cy="toggle-edit-futures-keys"
          variant="text"
          class="!p-2"
          icon
          @click="toggle()"
        >
          <RuiIcon
            size="20"
            :name="!editing ? 'lu-pencil' : 'lu-x'"
          />
        </RuiButton>
      </template>
      {{ !editing ? t('exchange_keys_form.edit.activate_tooltip') : t('exchange_keys_form.edit.deactivate_tooltip') }}
    </RuiTooltip>
  </div>

  <Component
    :is="inputComponent"
    v-model.trim="keyModel"
    variant="outlined"
    color="primary"
    :disabled="masked"
    :error-messages="keyErrors"
    data-cy="kraken-futures-api-key"
    prepend-icon="lu-key"
    :label="t('exchange_settings.inputs.futures_api_key')"
  />
  <Component
    :is="inputComponent"
    v-model.trim="secretModel"
    variant="outlined"
    color="primary"
    :disabled="masked"
    :error-messages="secretErrors"
    data-cy="kraken-futures-api-secret"
    prepend-icon="lu-lock-keyhole"
    :label="t('exchange_settings.inputs.futures_api_secret')"
  />
</template>
