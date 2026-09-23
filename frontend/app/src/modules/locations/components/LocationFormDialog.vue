<script setup lang="ts">
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { DialogType } from '@/modules/core/common/dialogs';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { noSubmit, useForm } from '@/modules/core/form/use-form';
import LocationIconPicker from '@/modules/locations/components/LocationIconPicker.vue';
import LocationImageField from '@/modules/locations/components/LocationImageField.vue';
import {
  locationEditPayload,
  type LocationFormData,
  locationFormSchema,
  type LocationFormState,
  parentCandidates,
  toLocationFormState,
} from '@/modules/locations/location-form';
import { useLocationManagement } from '@/modules/locations/use-location-management';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<LocationFormData | undefined>({ required: true });

const emit = defineEmits<{
  created: [location: LocationNode];
  /** A location was created or changed, so its row can be brought into view. */
  saved: [identifier: string];
}>();

const submitting = ref<boolean>(false);
const pendingImage = ref<File | null>();

const { t } = useI18n({ useScope: 'global' });

const treeStore = useLocationTreeStore();
const { nodes } = storeToRefs(treeStore);
const { show } = useConfirmStore();
const { setMessage } = useMessageStore();
const { createLocation, editLocation, previewEdit, removeImage, uploadImage } = useLocationManagement();

const form = useForm<LocationFormState, LocationFormState>({
  initial: (): LocationFormState => {
    const data = get(modelValue);
    return data ? toLocationFormState(data) : toLocationFormState({ mode: 'add', parentIdentifier: '' });
  },
  schema: locationFormSchema(),
  submit: noSubmit,
  transform: (state): LocationFormState => ({ ...state }),
});

const editedLocation = computed(() => {
  const data = get(modelValue);
  return data?.mode === 'edit' ? treeStore.getNode(data.location.identifier) ?? data.location : undefined;
});

const dirty = computed<boolean>(() => get(form.dirty) || get(pendingImage) !== undefined);

const parents = computed<string[]>(() => {
  const location = get(editedLocation);
  return parentCandidates(get(nodes), location ? treeStore.subtreeOf(location.identifier) : new Set());
});

watch(modelValue, (data) => {
  set(pendingImage, undefined);
  if (data)
    form.reset(toLocationFormState(data));
});

function close(): void {
  set(modelValue, undefined);
}

function reportFailure(message: string, title: string = t('location_manager.form.error')): void {
  setMessage({ description: message, title });
}

/**
 * Uploads or removes the image the user chose, once the location exists. The location itself is
 * already saved at this point, so a failed image is reported without undoing it.
 */
async function saveImage(identifier: string): Promise<void> {
  const image = get(pendingImage);
  if (image === undefined)
    return;
  const outcome = image ? await uploadImage(identifier, image) : await removeImage(identifier);
  if (!outcome.ok)
    reportFailure(outcome.error, t('location_manager.image.error'));
}

async function create(): Promise<void> {
  const { icon, name, parentIdentifier } = form.state;
  const outcome = await createLocation({ icon, name: name.trim(), parentIdentifier });
  if (!outcome.ok)
    return reportFailure(outcome.error);
  await saveImage(outcome.value.identifier);
  emit('created', outcome.value);
  emit('saved', outcome.value.identifier);
  close();
}

async function saveEdit(identifier: string, payload: ReturnType<typeof locationEditPayload>): Promise<void> {
  if (Object.keys(payload).length > 0) {
    const outcome = await editLocation(identifier, payload);
    if (!outcome.ok)
      return reportFailure(outcome.error);
  }
  await saveImage(identifier);
  emit('saved', identifier);
  close();
}

/**
 * Moving a location changes which totals its history counts towards, so the move is checked
 * first and only saved once the user confirms the old and new paths.
 */
async function edit(identifier: string): Promise<void> {
  const location = get(editedLocation);
  if (!location)
    return;
  const payload = locationEditPayload(location, form.state);
  if (payload.parentIdentifier === undefined)
    return saveEdit(identifier, payload);

  const preview = await previewEdit(identifier, payload);
  if (!preview.ok)
    return reportFailure(preview.error);
  show({
    message: t('location_manager.move.message', {
      new: preview.value.newPath.slice(1).join(' › '),
      old: preview.value.oldPath.slice(1).join(' › '),
    }),
    primaryAction: t('location_manager.move.confirm'),
    title: t('location_manager.move.title'),
    type: DialogType.INFO,
  }, async () => saveEdit(identifier, payload));
}

async function save(): Promise<void> {
  const data = get(modelValue);
  if (!data || !form.validate())
    return;
  set(submitting, true);
  try {
    if (data.mode === 'add')
      await create();
    else
      await edit(data.location.identifier);
  }
  finally {
    set(submitting, false);
  }
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="modelValue?.mode === 'edit' ? t('location_manager.form.edit_title') : t('location_manager.form.add_title')"
    :action="{ primary: t('common.actions.save') }"
    :loading="submitting"
    :layout="{ autoHeight: true, maxWidth: '640px' }"
    :prompt-on-close="dirty"
    @confirm="save()"
    @cancel="close()"
  >
    <div
      v-if="modelValue"
      class="flex flex-col gap-4"
      data-testid="location-form"
    >
      <RuiTextField
        v-model="form.state.name"
        variant="outlined"
        color="primary"
        :label="t('common.name')"
        :hint="t('location_manager.form.name_hint')"
        :error-messages="form.errors('name')"
        data-testid="location-form-name"
        @update:model-value="form.touch('name')"
      />
      <LocationSelector
        v-model="form.state.parentIdentifier"
        :items="parents"
        :label="t('location_manager.form.parent')"
        :error-messages="form.errors('parentIdentifier')"
        data-testid="location-form-parent"
        @update:model-value="form.touch('parentIdentifier')"
      />
      <LocationIconPicker v-model="form.state.icon" />
      <LocationImageField
        v-model="pendingImage"
        :icon="form.state.icon"
        :identifier="editedLocation?.identifier"
        :image="editedLocation?.image ?? null"
      />
    </div>
  </BigDialog>
</template>
