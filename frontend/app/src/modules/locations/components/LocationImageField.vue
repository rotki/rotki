<script setup lang="ts">
import type { LocationIcon } from '@/modules/locations/location-icons';
import { locationImageUrl } from '@/modules/locations/use-location-tree-api';
import AppImage from '@/modules/shell/components/AppImage.vue';

/**
 * The image the form will save: a file to upload, `null` to remove the stored image, or
 * `undefined` to keep whatever is stored. Nothing is sent before the form is saved.
 */
const pending = defineModel<File | null | undefined>({ required: true });

const { icon, identifier, image } = defineProps<{
  /** The icon shown while there is no image. */
  icon: LocationIcon;
  /** The location being edited, absent while one is created. */
  identifier?: string;
  /** The stored image of the location being edited. */
  image: string | null;
}>();

const { t } = useI18n({ useScope: 'global' });

/** Whether the user asked to remove the stored image, which choosing and then clearing a file keeps. */
const removingStored = ref<boolean>(false);

const pendingUrl = useObjectUrl(() => pending.value ?? undefined);

const storedUrl = computed<string | undefined>(() =>
  identifier && image ? locationImageUrl(identifier, image) : undefined);

/**
 * The chosen file, if any. Clearing it in the dropzone goes back to the stored image, or to no
 * image when the user had removed the stored one.
 */
const chosen = computed<File | undefined>({
  get: () => get(pending) ?? undefined,
  set: value => set(pending, value ?? (get(removingStored) ? null : undefined)),
});

const previewUrl = computed<string | undefined>(() => {
  const value = get(pending);
  if (value === null)
    return undefined;
  return value ? get(pendingUrl) : get(storedUrl);
});

const canRemoveStored = computed<boolean>(() => get(pending) === undefined && get(storedUrl) !== undefined);

/** Leaves the location without an image once the form is saved. */
function removeStored(): void {
  set(removingStored, true);
  set(pending, null);
}

watch(pending, (value) => {
  if (value === undefined)
    set(removingStored, false);
});
</script>

<template>
  <div
    class="flex items-start gap-4"
    data-testid="location-image-field"
  >
    <div class="size-10 mt-2 shrink-0 flex items-center justify-center">
      <AppImage
        v-if="previewUrl"
        :src="previewUrl"
        size="40px"
        fit="contain"
        data-testid="location-image-preview"
      />
      <RuiIcon
        v-else
        :name="icon"
        color="secondary"
        size="32"
      />
    </div>
    <div class="flex flex-col gap-1 grow min-w-0">
      <RuiFileUpload
        v-model="chosen"
        accept=".png,.svg,.jpeg,.jpg,.webp"
        :upload-text="t('file_upload.dropzone.prefix')"
        :click-to-upload-text="t('file_upload.dropzone.choose')"
        :replace-text="t('file_upload.dropzone.replace')"
        :hint="t('location_manager.image.hint')"
        details="auto"
        data-testid="location-image-upload"
      />
      <RuiButton
        v-if="canRemoveStored"
        class="self-start"
        size="sm"
        variant="text"
        color="error"
        data-testid="location-image-remove"
        @click="removeStored()"
      >
        {{ t('location_manager.image.remove') }}
      </RuiButton>
    </div>
  </div>
</template>
