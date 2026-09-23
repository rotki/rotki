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

const fileInput = useTemplateRef<HTMLInputElement>('fileInput');
const pendingUrl = useObjectUrl(() => pending.value ?? undefined);

const storedUrl = computed<string | undefined>(() =>
  identifier && image ? locationImageUrl(identifier, image) : undefined);

const previewUrl = computed<string | undefined>(() => {
  const value = get(pending);
  if (value === null)
    return undefined;
  return value ? get(pendingUrl) : get(storedUrl);
});

function choose(event: Event): void {
  const input = event.target;
  if (!(input instanceof HTMLInputElement) || !input.files?.[0])
    return;
  set(pending, input.files[0]);
  input.value = '';
}

/** Leaves the location without an image: the stored one goes on save, a chosen file is dropped. */
function remove(): void {
  set(pending, get(storedUrl) === undefined ? undefined : null);
}
</script>

<template>
  <div
    class="flex items-center gap-4"
    data-testid="location-image-field"
  >
    <div class="size-10 shrink-0 flex items-center justify-center">
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
    <div class="flex flex-col gap-1">
      <span class="text-body-2 text-rui-text-secondary">{{ t('location_manager.image.hint') }}</span>
      <div class="flex gap-2">
        <RuiButton
          size="sm"
          data-testid="location-image-upload"
          @click="fileInput?.click()"
        >
          {{ previewUrl ? t('location_manager.image.replace') : t('location_manager.image.upload') }}
        </RuiButton>
        <RuiButton
          v-if="previewUrl"
          size="sm"
          variant="text"
          color="error"
          data-testid="location-image-remove"
          @click="remove()"
        >
          {{ t('location_manager.image.remove') }}
        </RuiButton>
      </div>
    </div>
    <input
      ref="fileInput"
      type="file"
      class="hidden"
      accept=".png,.svg,.jpeg,.jpg,.webp"
      data-testid="location-image-input"
      @change="choose($event)"
    />
  </div>
</template>
