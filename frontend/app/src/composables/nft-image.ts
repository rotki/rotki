import { api } from '@/services/rotkehlchen-api';

export function useNftImage(mediaUrl: Ref<string | null>) {
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

  const isVideo: Ref<boolean> = ref(false);

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
    shouldRender,
    isVideo,
    renderedMedia,
  };
}
