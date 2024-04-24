import { api } from '@/services/rotkehlchen-api';
import type { MaybeRef } from '@vueuse/core';

export function useNftImage(mediaUrl: MaybeRef<string | null>) {
  const { shouldRenderImage } = useNfts();

  const isMediaVideo = async (url: string): Promise<boolean> => {
    try {
      const response = await api.instance.head(url);
      const contentType = response.headers['content-type'];
      return contentType.startsWith('video');
    }
    catch {
      return false;
    }
  };

  const placeholder = './assets/images/placeholder.svg';

  const shouldRender: ComputedRef<boolean> = computed(() => {
    const media = get(mediaUrl);

    if (!media)
      return true;

    return shouldRenderImage(media);
  });

  const checkingType: Ref<boolean> = ref(false);

  const isVideo = asyncComputed(() => {
    const media = get(mediaUrl);
    if (!media || !get(shouldRender))
      return false;

    return isMediaVideo(media);
  }, false, { evaluating: checkingType });

  const renderedMedia = computed(() => {
    const media = get(mediaUrl);
    if (get(checkingType) || !media || !get(shouldRender))
      return placeholder;

    return media;
  });

  return {
    shouldRender,
    isVideo,
    renderedMedia,
  };
}
