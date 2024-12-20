<script setup lang="ts">
import domtoimage from 'dom-to-image';
import AppImage from '@/components/common/AppImage.vue';
import WrappedConfetti from '@/components/wrapped/WrappedConfetti.vue';
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import { scoresData } from '@/composables/api/statistics/wrap';
import { useSessionSettingsStore } from '@/store/settings/session';
import { downloadFileByUrl } from '@/utils/download';
import { logger } from '@/utils/logging';

const props = defineProps<{
  score: number;
  isCurrentYear: boolean;
}>();

const wrapper = ref();

const { t } = useI18n();

const { animationsEnabled } = storeToRefs(useSessionSettingsStore());
const { isDark } = useRotkiTheme();

const scoreCategory = computed(() => {
  if (!props.score) {
    return scoresData[0];
  }

  return scoresData
    .slice()
    .reverse()
    .find(category => props.score >= category.min) ?? scoresData[0];
});

async function downloadImage() {
  const wrapperVal = get(wrapper);
  if (!wrapperVal)
    return;

  const width = wrapperVal.offsetWidth;
  const height = wrapperVal.offsetHeight;
  const scale = 2;

  domtoimage
    .toPng(wrapperVal, {
      height: height * scale,
      quality: 1,
      style: {
        backgroundColor: get(isDark) ? '#212125' : '#f6f7fa',
        height: `${height}px`,
        transform: `scale(${scale})`,
        transformOrigin: 'top left',
        width: `${width}px`,
      },
      width: width * scale,
    })
    .then((dataUrl) => {
      downloadFileByUrl(dataUrl, 'rotki-wrapped-score.png');
    })
    .catch((error) => {
      logger.error(error);
    });
}
</script>

<template>
  <div class="rounded-lg relative">
    <WrappedConfetti
      v-if="animationsEnabled"
      class="absolute top-0 left-0 w-full h-full"
    />
    <RuiButton
      class="absolute top-4 right-4 !px-2"
      color="primary"
      variant="text"
      size="sm"
      icon
      @click="downloadImage()"
    >
      <template #prepend>
        <RuiIcon
          name="external-link-line"
          size="12"
        />
      </template>

      {{ t('wrapped.share') }}
    </RuiButton>
    <div
      ref="wrapper"
      class="bg-rui-primary/[0.05] p-4 py-6 rounded-lg overflow-hidden text-center flex flex-col items-center gap-6"
    >
      <div>
        <div class="text-rui-text-secondary mb-1 font-mono">
          {{ t('wrapped.score_header') }}
        </div>
        <div class="text-rui-primary text-4xl font-bold font-mono">
          {{ score }}
        </div>
      </div>
      <AppImage
        class="rounded-xl overflow-hidden shadow-xl"
        :src="scoreCategory.imageUrl"
        width="320px"
      />
      <div class="flex flex-col items-center gap-2">
        <div class="text-h5 font-mono">
          <i18n-t
            v-if="isCurrentYear"
            keypath="wrapped.score_title"
            tag="div"
            class="font-mono flex gap-4"
          >
            <template #name>
              <div class="font-mono bg-rui-primary text-white font-bold px-4 rounded-md">
                {{ scoreCategory.name }}
              </div>
            </template>
          </i18n-t>
          <i18n-t
            v-else
            keypath="wrapped.score_title_period"
            tag="div"
            class="font-mono flex gap-4"
          >
            <template #name>
              <div class="font-mono bg-rui-primary text-white font-bold px-4 rounded-md">
                {{ scoreCategory.name }}
              </div>
            </template>
          </i18n-t>
        </div>
        <div class="text-rui-text-secondary text-sm font-italic">
          {{ scoreCategory.description }}
        </div>
      </div>
      <div class="text-xs flex items-center gap-1.5 mt-4">
        {{ t('wrapped.made_with_love') }}
        <RotkiLogo
          text
          size="1"
          class="!gap-1 [&>div]:!text-sm"
        />
      </div>
    </div>
  </div>
</template>
