<script setup lang="ts">
import type { BankFormData, BankManifest } from '@/modules/banks/types';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import {
  type BankConnectionFormState,
  bankConnectionSchema,
  emptyCredentials,
  isEditing,
  toBankConnectionFormState,
} from '@/modules/banks/bank-connection-form';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useMappedModelForm } from '@/modules/core/form/use-model-form';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const modelValue = defineModel<BankFormData>({ required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { required: true });
const errorMessages = defineModel<ValidationErrors>('errorMessages', { default: () => ({}) });

const { manifests } = storeToRefs(useBankConnectionsStore());
const { manifestFor } = useBankConnectionsStore();
const { t } = useI18n({ useScope: 'global' });

const editMode = computed<boolean>(() => isEditing(get(modelValue).mode));
const manifest = computed<BankManifest | undefined>(() => manifestFor(get(modelValue).location));

const form = useMappedModelForm<BankFormData, BankConnectionFormState>({
  model: modelValue,
  schema: computed(() => bankConnectionSchema(get(modelValue).mode, get(manifest))),
  serverErrors: errorMessages,
  stateUpdated,
  toModel: (state, entry): BankFormData => ({ ...entry, ...state }),
  toState: toBankConnectionFormState,
});

const name = computed<string>({
  get: () => (get(editMode) ? form.state.newName : form.state.name),
  set: (value: string) => {
    if (get(editMode))
      form.state.newName = value;
    else
      form.state.name = value;
  },
});

const nameErrors = computed<string[]>(() => form.errors(get(editMode) ? 'newName' : 'name'));

/** Switching the bank starts the credentials over: another bank has other slots. */
function selectLocation(location: string | undefined): void {
  form.state.location = location ?? '';
  form.state.credentials = emptyCredentials(location === undefined ? undefined : manifestFor(location));
}

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div
    class="flex flex-col gap-4"
    data-testid="bank-connection-form"
  >
    <RuiMenuSelect
      v-if="!editMode"
      :model-value="form.state.location"
      :options="manifests"
      :label="t('bank_settings.form.bank')"
      :error-messages="form.errors('location')"
      key-attr="location"
      text-attr="displayName"
      variant="outlined"
      data-testid="bank-connection-location"
      @update:model-value="selectLocation($event)"
    >
      <template #selection="{ item }">
        <LocationDisplay
          :identifier="item.location"
          :open-details="false"
        />
      </template>
      <template #item="{ item }">
        <LocationDisplay
          :identifier="item.location"
          :open-details="false"
        />
      </template>
    </RuiMenuSelect>
    <LocationDisplay
      v-else
      :identifier="form.state.location"
      :open-details="false"
    />

    <RuiTextField
      v-model="name"
      variant="outlined"
      color="primary"
      :label="t('bank_settings.form.name')"
      :hint="t('bank_settings.form.name_hint')"
      :error-messages="nameErrors"
      data-testid="bank-connection-name"
    />

    <RuiRevealableTextField
      v-for="secret in manifest?.secrets ?? []"
      :key="secret.slot"
      v-model="form.state.credentials[secret.slot]"
      variant="outlined"
      color="primary"
      :label="secret.label"
      :hint="editMode ? t('bank_settings.form.credential_keep_hint') : secret.description"
      :error-messages="form.errors(`credentials.${secret.slot}`)"
      :data-testid="`bank-connection-secret-${secret.slot}`"
    />

    <RuiAlert
      v-if="manifest && manifest.setupNotes.length > 0"
      type="info"
      data-testid="bank-connection-notes"
    >
      <ul class="list-disc pl-4 flex flex-col gap-1">
        <li
          v-for="(note, index) in manifest.setupNotes"
          :key="index"
        >
          {{ note }}
        </li>
      </ul>
      <ExternalLink
        v-if="manifest.docsUrl"
        class="mt-2"
        :text="t('bank_settings.form.docs')"
        :url="manifest.docsUrl"
      />
    </RuiAlert>
  </div>
</template>
