<script setup lang="ts">
import type { BankFormData, BankManifest } from '@/modules/banks/types';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import {
  type BankConnectionFormState,
  bankConnectionSchema,
  emptyCredentials,
  isEditing,
  needsBankLocation,
  toBankConnectionFormState,
} from '@/modules/banks/bank-connection-form';
import { bankLocations } from '@/modules/banks/bank-locations';
import BankConnectorDisplay from '@/modules/banks/components/BankConnectorDisplay.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useMappedModelForm } from '@/modules/core/form/use-model-form';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const modelValue = defineModel<BankFormData>({ required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { required: true });
const errorMessages = defineModel<ValidationErrors>('errorMessages', { default: () => ({}) });

const { manifests } = storeToRefs(useBankConnectionsStore());
const { manifestFor } = useBankConnectionsStore();
const { t } = useI18n({ useScope: 'global' });

const connector = ref<string>(get(modelValue).connector);

const { nodes: locationTree } = storeToRefs(useLocationTreeStore());

const editMode = computed<boolean>(() => isEditing(get(modelValue).mode));
const manifest = computed<BankManifest | undefined>(() => manifestFor(get(connector)));
const banks = computed<string[]>(() => bankLocations(get(locationTree)));
const choosesLocation = computed<boolean>(() => !get(editMode) && needsBankLocation(get(manifest)));

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

/**
 * Switching the connector starts the credentials and the bank over: another connector has other
 * slots, and may fix the bank its data belongs to.
 */
function selectConnector(selection: string | undefined): void {
  const selected = selection === undefined ? undefined : manifestFor(selection);
  set(connector, selection ?? '');
  form.state.connector = selection ?? '';
  form.state.location = selected?.fixedLocation ?? '';
  form.state.credentials = emptyCredentials(selected);
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
    <LocationDisplay
      v-if="editMode"
      :identifier="form.state.location"
      :open-details="false"
    />
    <template v-else>
      <RuiMenuSelect
        :model-value="form.state.connector"
        :options="manifests"
        :label="t('bank_settings.form.connector')"
        :error-messages="form.errors('connector')"
        key-attr="connectorIdentifier"
        text-attr="displayName"
        variant="outlined"
        data-testid="bank-connection-connector"
        @update:model-value="selectConnector($event)"
      >
        <template #selection="{ item }">
          <BankConnectorDisplay :manifest="item" />
        </template>
        <template #item="{ item }">
          <BankConnectorDisplay :manifest="item" />
        </template>
      </RuiMenuSelect>
      <LocationSelector
        v-if="choosesLocation"
        v-model="form.state.location"
        :items="banks"
        :label="t('bank_settings.form.bank')"
        :hint="t('bank_settings.form.bank_hint')"
        :error-messages="form.errors('location')"
        data-testid="bank-connection-location"
      />
    </template>

    <RuiTextField
      v-model="name"
      variant="outlined"
      color="primary"
      :label="t('bank_settings.form.name')"
      :hint="t('bank_settings.form.name_hint')"
      :error-messages="nameErrors"
      data-testid="bank-connection-name"
    />

    <template
      v-for="secret in manifest?.secrets ?? []"
      :key="secret.slot"
    >
      <RuiRevealableTextField
        v-if="secret.secret"
        v-model="form.state.credentials[secret.slot]"
        variant="outlined"
        color="primary"
        :label="secret.label"
        :hint="editMode ? t('bank_settings.form.credential_keep_hint') : secret.description"
        :error-messages="form.errors(`credentials.${secret.slot}`)"
        :data-testid="`bank-connection-secret-${secret.slot}`"
      />
      <RuiTextField
        v-else
        v-model="form.state.credentials[secret.slot]"
        variant="outlined"
        color="primary"
        :label="secret.label"
        :hint="editMode ? t('bank_settings.form.credential_keep_hint') : secret.description"
        :error-messages="form.errors(`credentials.${secret.slot}`)"
        :data-testid="`bank-connection-secret-${secret.slot}`"
      />
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
