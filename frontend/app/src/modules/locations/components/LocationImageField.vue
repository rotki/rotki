<script setup lang="ts">
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useLocationManagement } from '@/modules/locations/use-location-management';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

const { identifier, image } = defineProps<{
  identifier: string;
  image: string | null;
}>();

const busy = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const { setMessage } = useMessageStore();
const { removeImage, uploadImage } = useLocationManagement();
const fileInput = useTemplateRef<HTMLInputElement>('fileInput');

function reportFailure(message: string): void {
  setMessage({ description: message, title: t('location_manager.image.error') });
}

async function upload(event: Event): Promise<void> {
  const input = event.target;
  if (!(input instanceof HTMLInputElement) || !input.files?.[0])
    return;
  set(busy, true);
  const outcome = await uploadImage(identifier, input.files[0]);
  set(busy, false);
  input.value = '';
  if (!outcome.ok)
    reportFailure(outcome.error);
}

async function remove(): Promise<void> {
  set(busy, true);
  const outcome = await removeImage(identifier);
  set(busy, false);
  if (!outcome.ok)
    reportFailure(outcome.error);
}
</script>

<template>
  <div
    class="flex items-center gap-4"
    data-testid="location-image-field"
  >
    <LocationIcon
      :item="identifier"
      icon
      size="40px"
    />
    <div class="flex flex-col gap-1">
      <span class="text-body-2 text-rui-text-secondary">{{ t('location_manager.image.hint') }}</span>
      <div class="flex gap-2">
        <RuiButton
          size="sm"
          :loading="busy"
          data-testid="location-image-upload"
          @click="fileInput?.click()"
        >
          {{ image ? t('location_manager.image.replace') : t('location_manager.image.upload') }}
        </RuiButton>
        <RuiButton
          v-if="image"
          size="sm"
          variant="text"
          color="error"
          :disabled="busy"
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
      @change="upload($event)"
    />
  </div>
</template>
