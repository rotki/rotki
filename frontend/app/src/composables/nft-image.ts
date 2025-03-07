import type { ComputedRef, Ref } from 'vue';
import { useNfts } from '@/composables/assets/nft';
import { api } from '@/services/rotkehlchen-api';

interface UseNftImageReturnType {
  shouldRender: ComputedRef<boolean>;
  isVideo: Ref<boolean>;
  renderedMedia: ComputedRef<string>;
}

export function useNftImage(mediaUrl: Ref<string | null>): UseNftImageReturnType {
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

  const placeholder = './assets/images/placeholder/image.svg';

  const shouldRender = computed<boolean>(() => {
    const media = get(mediaUrl);

    if (!media)
      return true;

    return shouldRenderImage(media);
  });

  const checkingType = ref<boolean>(false);

  const isVideo = ref<boolean>(false);

  watch([mediaUrl, shouldRender], async ([media, shouldRender], [prevMedia, prevShouldRender]) => {
    if (media === prevMedia && shouldRender === prevShouldRender)
      return;

    if (!media || !shouldRender) {
      set(isVideo, false);
      return;
    }

    set(checkingType, true);
    set(isVideo, await isMediaVideo(media));
    set(checkingType, false);
  });

  const renderedMedia = computed(() => {
    const media = get(mediaUrl);
    if (get(checkingType) || !media || !get(shouldRender))
      return placeholder;

    return media;
  });

  return {
    isVideo,
    renderedMedia,
    shouldRender,
  };
}
