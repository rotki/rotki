import type { ComputedRef, Ref } from 'vue';
import type { GalleryNft } from '@/types/nfts';
import { type TablePaginationData, useBreakpoint } from '@rotki/ui-library';

interface UseNftGalleryLayoutReturn {
  firstLimit: ComputedRef<number>;
  itemsPerPage: Ref<number>;
  limits: ComputedRef<number[]>;
  page: Ref<number>;
  paginationData: ComputedRef<TablePaginationData>;
  visibleNfts: ComputedRef<GalleryNft[]>;
}

export function useNftGalleryLayout(
  items: ComputedRef<GalleryNft[]>,
): UseNftGalleryLayoutReturn {
  // State
  const page = ref<number>(1);
  const itemsPerPage = ref<number>(8);

  // Breakpoint composable
  const { is2xl, isMd, isSm, isSmAndDown } = useBreakpoint();

  // Computed properties
  const firstLimit = computed<number>(() => {
    if (get(isSmAndDown))
      return 1;

    if (get(isSm))
      return 2;

    if (get(isMd))
      return 6;

    if (get(is2xl))
      return 10;

    return 8;
  });

  const limits = computed<number[]>(() => {
    const first = get(firstLimit);
    return [first, first * 2, first * 4];
  });

  const paginationData = computed<TablePaginationData>({
    get() {
      return {
        limit: get(itemsPerPage),
        limits: get(limits),
        page: get(page),
        total: get(items).length,
      };
    },
    set(value: TablePaginationData) {
      set(page, value.page);
      set(itemsPerPage, value.limit);
    },
  });

  const visibleNfts = computed<GalleryNft[]>(() => {
    const perPage = get(itemsPerPage);
    const start = (get(page) - 1) * perPage;
    return get(items).slice(start, start + perPage);
  });

  // Watch for responsive changes
  watchImmediate(firstLimit, () => {
    set(itemsPerPage, get(firstLimit));
  });

  return {
    firstLimit,
    itemsPerPage,
    limits,
    page,
    paginationData,
    visibleNfts,
  };
}
