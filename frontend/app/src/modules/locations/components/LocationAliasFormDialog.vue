<script setup lang="ts">
import type { ResultAsync } from 'plainfp/result-async';
import type { DeepReadonly } from 'vue';
import type { LocationAliases } from '@/modules/locations/use-location-tree-api';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { sameAlias } from '@/modules/locations/use-location-aliases';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const display = defineModel<boolean>({ required: true });

const { aliases, save } = defineProps<{
  /** The saved aliases, to tell the user when the alias typed already exists. */
  aliases: DeepReadonly<LocationAliases>;
  /** Saves the alias, handing back why it was refused. */
  save: (alias: string, locationIdentifier: string) => ResultAsync<void, string>;
}>();

const alias = ref<string>('');
const target = ref<string>('');
const submitting = ref<boolean>(false);
/** Why the last save was refused; the dialog stays open, so it is named there. */
const saveFailure = shallowRef<string>();

const { t } = useI18n({ useScope: 'global' });

const { pathLabelOf } = useLocationTreeStore();

/** The saved alias with the name typed, compared without case as the backend does. */
const existing = computed<DeepReadonly<LocationAliases[number]> | undefined>(() => {
  const name = get(alias).trim();
  return name === '' ? undefined : aliases.find(entry => sameAlias(entry.alias, name));
});

/** Whether saving points an alias that already exists at another location. */
const moving = computed<boolean>(() => {
  const found = get(existing);
  return found !== undefined && get(target) !== '' && found.locationIdentifier !== get(target);
});

const canSave = computed<boolean>(() => get(alias).trim() !== '' && get(target) !== ''
  && get(existing)?.locationIdentifier !== get(target));

/** What the alias typed already does, and what saving it would change. */
const notice = computed<string | undefined>(() => {
  const found = get(existing);
  if (!found)
    return undefined;
  const values = { alias: found.alias, location: pathLabelOf(found.locationIdentifier) };
  return get(moving) ? t('location_manager.aliases.move_notice', values) : t('location_manager.aliases.exists', values);
});

const dirty = computed<boolean>(() => get(alias) !== '' || get(target) !== '');

watch(display, (open) => {
  if (!open)
    return;
  set(alias, '');
  set(target, '');
  set(saveFailure, undefined);
});

function close(): void {
  set(display, false);
}

async function confirm(): Promise<void> {
  if (!get(canSave))
    return;
  set(submitting, true);
  set(saveFailure, undefined);
  try {
    const outcome = await save(get(alias), get(target));
    if (outcome.ok)
      close();
    else
      set(saveFailure, outcome.error);
  }
  finally {
    set(submitting, false);
  }
}
</script>

<template>
  <BigDialog
    :display="display"
    :title="t('location_manager.aliases.add')"
    :action="{ disabled: !canSave, primary: moving ? t('location_manager.aliases.move') : t('location_manager.aliases.add') }"
    :loading="submitting"
    :layout="{ autoHeight: true, maxWidth: '640px' }"
    :prompt-on-close="dirty"
    @confirm="confirm()"
    @cancel="close()"
  >
    <div
      v-if="display"
      class="flex flex-col gap-4"
      data-testid="location-alias-form"
    >
      <p class="text-body-2 text-rui-text-secondary m-0">
        {{ t('location_manager.aliases.subtitle') }}
      </p>
      <FailureStrip
        v-if="saveFailure"
        :title="t('location_manager.aliases.error')"
        :failure="saveFailure"
        :retryable="false"
        data-testid="location-alias-form-error"
      />
      <RuiTextField
        v-model="alias"
        color="primary"
        :label="t('location_manager.aliases.alias')"
        data-testid="location-alias-name"
      />
      <LocationSelector
        v-model="target"
        :label="t('common.location')"
        data-testid="location-alias-target"
      />
      <RuiAlert
        v-if="existing"
        :type="moving ? 'warning' : 'info'"
        data-testid="location-alias-existing"
      >
        {{ notice }}
      </RuiAlert>
    </div>
  </BigDialog>
</template>
