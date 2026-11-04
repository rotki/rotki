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
import { type BankSelectionOption, toManifestSelection } from '@/modules/banks/bank-connection-selection';
import BankConnectionPicker from '@/modules/banks/components/BankConnectionPicker.vue';
import BankLabel from '@/modules/banks/components/BankLabel.vue';
import FinTsConnectionFields from '@/modules/banks/components/FinTsConnectionFields.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useMappedModelForm } from '@/modules/core/form/use-model-form';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const modelValue = defineModel<BankFormData>({ required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { required: true });
const errorMessages = defineModel<ValidationErrors>('errorMessages', { default: () => ({}) });

const { manifests } = storeToRefs(useBankConnectionsStore());
const { bankNameFor, manifestFor } = useBankConnectionsStore();
const { t } = useI18n({ useScope: 'global' });

const editMode = computed<boolean>(() => isEditing(get(modelValue).mode));
const manifest = computed<BankManifest | undefined>(() => manifestFor(get(modelValue).connector));
const fintsAddMode = computed<boolean>(() => !get(editMode) && get(modelValue).connector === 'fints');
const selectedOption = ref<BankSelectionOption>();

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
function selectBank(option: BankSelectionOption | undefined): void {
  set(selectedOption, option);
  form.state.connector = option?.connector ?? '';
  form.state.credentials = emptyCredentials(option === undefined ? undefined : manifestFor(option.connector));
}

watch(manifests, (available) => {
  if (get(selectedOption) || !form.state.connector)
    return;
  const selectedManifest = available.find(item => item.connector === form.state.connector);
  if (selectedManifest)
    set(selectedOption, toManifestSelection(selectedManifest, t('bank_settings.form.bank_other_fints')));
}, { immediate: true });

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div
    class="flex flex-col gap-4"
    data-testid="bank-connection-form"
  >
    <p
      v-if="!editMode"
      class="m-0 text-body-2 text-rui-text-secondary"
      data-testid="bank-connection-privacy"
    >
      {{ t('bank_settings.form.privacy') }}
    </p>
    <BankConnectionPicker
      v-if="!editMode"
      v-model="selectedOption"
      :manifests="manifests"
      :error-messages="form.errors('connector')"
      @update:model-value="selectBank($event)"
    />
    <BankLabel
      v-else
      :connector="form.state.connector"
      :name="bankNameFor(form.state.connector)"
      data-testid="bank-connection-bank"
    />

    <FinTsConnectionFields
      v-if="fintsAddMode && manifest"
      v-model:credentials="form.state.credentials"
      v-model:name="form.state.name"
      :manifest="manifest"
      :errors="form.errors"
      :bank="selectedOption?.bank"
      :manual="selectedOption?.kind === 'fints-manual'"
    />

    <RuiTextField
      v-else
      v-model="name"
      color="primary"
      :label="t('bank_settings.form.name')"
      :hint="t('bank_settings.form.name_hint')"
      :error-messages="nameErrors"
      data-testid="bank-connection-name"
    />

    <template v-if="!fintsAddMode">
      <template
        v-for="secret in manifest?.secrets ?? []"
        :key="secret.slot"
      >
        <RuiRevealableTextField
          v-if="secret.secret"
          v-model="form.state.credentials[secret.slot]"
          color="primary"
          :label="secret.label"
          :hint="editMode ? t('bank_settings.form.credential_keep_hint') : secret.description"
          :error-messages="form.errors(`credentials.${secret.slot}`)"
          :data-testid="`bank-connection-secret-${secret.slot}`"
        />
        <RuiTextField
          v-else
          v-model="form.state.credentials[secret.slot]"
          color="primary"
          :label="secret.label"
          :hint="editMode ? t('bank_settings.form.credential_keep_hint') : secret.description"
          :error-messages="form.errors(`credentials.${secret.slot}`)"
          :data-testid="`bank-connection-secret-${secret.slot}`"
        />
      </template>
    </template>

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
