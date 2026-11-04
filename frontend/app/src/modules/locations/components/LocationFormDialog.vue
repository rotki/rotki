<script setup lang="ts">
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
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
import { LOCATION_PATH_SEPARATOR } from '@/modules/locations/location-path';
import { useLocationManagement } from '@/modules/locations/use-location-management';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const modelValue = defineModel<LocationFormData | undefined>({ required: true });

const emit = defineEmits<{
  /** A location was created or changed, so its row can be brought into view. */
  saved: [identifier: string];
}>();

const submitting = ref<boolean>(false);
const pendingImage = ref<File | null>();
/** Why the last save was refused; the dialog stays open, so it is named there. */
const saveFailure = shallowRef<string>();
/** Why the chosen image could not be stored on a location that was saved. */
const imageFailure = shallowRef<string>();
/** The move the backend accepted, shown for the user to confirm with a second save. */
const pendingMove = shallowRef<{ parentIdentifier: string; oldPath: string; newPath: string }>();
/** A location just created whose image failed, which the dialog goes on editing with the image kept. */
let retryImageFor: string | undefined;

const { t } = useI18n({ useScope: 'global' });

const treeStore = useLocationTreeStore();
const { nodes } = storeToRefs(treeStore);
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

const editedLocation = computed<LocationNode | undefined>(() => {
  const data = get(modelValue);
  return data?.mode === 'edit' ? treeStore.getNode(data.location.identifier) ?? data.location : undefined;
});

const dirty = computed<boolean>(() => get(form.dirty) || get(pendingImage) !== undefined);

const parents = computed<string[]>(() => {
  const location = get(editedLocation);
  return treeStore.sortByTree(parentCandidates(get(nodes), location ? treeStore.subtreeOf(location.identifier) : new Set()));
});

watch(modelValue, (data) => {
  const keepImage = data?.mode === 'edit' && data.location.identifier === retryImageFor;
  retryImageFor = undefined;
  if (!keepImage) {
    set(pendingImage, undefined);
    set(imageFailure, undefined);
  }
  set(saveFailure, undefined);
  set(pendingMove, undefined);
  if (data)
    form.reset(toLocationFormState(data));
});

watch(() => form.state.parentIdentifier, () => {
  set(pendingMove, undefined);
});

function close(): void {
  set(modelValue, undefined);
}

/**
 * Uploads or removes the image the user chose, once the location exists, and tells whether that
 * worked. The location itself is already saved at this point, so a failed image does not undo
 * it: the dialog stays open on the saved location to retry the image or close.
 */
async function saveImage(identifier: string): Promise<boolean> {
  const image = get(pendingImage);
  if (image === undefined)
    return true;
  const outcome = image ? await uploadImage(identifier, image) : await removeImage(identifier);
  if (outcome.ok)
    return true;
  set(imageFailure, outcome.error);
  return false;
}

async function create(): Promise<void> {
  const { icon, name, parentIdentifier } = form.state;
  const outcome = await createLocation({ icon, name: name.trim(), parentIdentifier });
  if (!outcome.ok) {
    set(saveFailure, outcome.error);
    return;
  }
  const created = outcome.value;
  emit('saved', created.identifier);
  if (await saveImage(created.identifier)) {
    close();
    return;
  }
  retryImageFor = created.identifier;
  set(modelValue, { location: created, mode: 'edit' });
}

async function saveEdit(identifier: string, payload: ReturnType<typeof locationEditPayload>): Promise<void> {
  if (Object.keys(payload).length > 0) {
    const outcome = await editLocation(identifier, payload);
    if (!outcome.ok) {
      set(saveFailure, outcome.error);
      return;
    }
    form.reset(toLocationFormState({ location: outcome.value.location, mode: 'edit' }));
    set(pendingMove, undefined);
  }
  emit('saved', identifier);
  if (await saveImage(identifier))
    close();
}

/**
 * Moving a location changes which totals its history counts towards, so a move is first checked
 * and shown with its old and new path, and only saved by a second save of the same move.
 */
async function edit(identifier: string): Promise<void> {
  const location = get(editedLocation);
  if (!location)
    return;
  const payload = locationEditPayload(location, form.state);
  const parentIdentifier = payload.parentIdentifier;
  if (parentIdentifier === undefined || get(pendingMove)?.parentIdentifier === parentIdentifier)
    return saveEdit(identifier, payload);

  const preview = await previewEdit(identifier, payload);
  if (!preview.ok) {
    set(saveFailure, preview.error);
    return;
  }
  set(pendingMove, {
    newPath: preview.value.newPath.slice(1).join(LOCATION_PATH_SEPARATOR),
    oldPath: preview.value.oldPath.slice(1).join(LOCATION_PATH_SEPARATOR),
    parentIdentifier,
  });
}

/** Shows the dialog as busy while a save runs. */
async function saving(run: () => Promise<void>): Promise<void> {
  set(submitting, true);
  try {
    await run();
  }
  finally {
    set(submitting, false);
  }
}

async function save(): Promise<void> {
  const data = get(modelValue);
  if (!data || !form.validate())
    return;
  set(saveFailure, undefined);
  set(imageFailure, undefined);
  await saving(async () => (data.mode === 'add' ? create() : edit(data.location.identifier)));
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="modelValue?.mode === 'edit' ? t('location_manager.form.edit_title') : t('location_manager.form.add_title')"
    :action="{ primary: pendingMove ? t('location_manager.move.confirm') : t('common.actions.save') }"
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
      <FailureStrip
        v-if="saveFailure"
        :title="t('location_manager.form.error')"
        :failure="saveFailure"
        :retryable="false"
        data-testid="location-form-error"
      />
      <RuiTextField
        v-model="form.state.name"
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
      <RuiAlert
        v-if="pendingMove"
        type="info"
        :title="t('location_manager.move.title')"
        data-testid="location-form-move"
      >
        <span class="whitespace-pre-line">{{ t('location_manager.move.message', { new: pendingMove.newPath, old: pendingMove.oldPath }) }}</span>
      </RuiAlert>
      <LocationIconPicker v-model="form.state.icon" />
      <FailureStrip
        v-if="imageFailure"
        :title="t('location_manager.image.error')"
        :failure="imageFailure"
        :retryable="false"
        data-testid="location-form-image-error"
      />
      <LocationImageField
        v-model="pendingImage"
        :icon="form.state.icon"
        :identifier="editedLocation?.identifier"
        :image="editedLocation?.image ?? null"
      />
    </div>
  </BigDialog>
</template>
