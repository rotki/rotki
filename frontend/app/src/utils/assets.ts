import { ManagedAsset } from '@/components/asset-manager/types';

export function compareAssets(
  a: ManagedAsset,
  b: ManagedAsset,
  element: keyof ManagedAsset,
  keyword: string,
  desc: boolean
): number {
  if (keyword.length > 0 && (element === 'symbol' || element === 'name')) {
    const first = a[element].toLocaleLowerCase();
    const second = b[element].toLocaleLowerCase();
    const aIndex = first.indexOf(keyword);
    const bIndex = second.indexOf(keyword);
    if (aIndex !== bIndex) {
      return desc ? bIndex - aIndex : aIndex - bIndex;
    }
  }

  const aElement = a[element];
  const bElement = b[element];

  if (typeof bElement === 'number' && typeof aElement === 'number') {
    return desc ? bElement - aElement : aElement - bElement;
  } else if (typeof bElement === 'string' && typeof aElement === 'string') {
    return desc
      ? bElement.localeCompare(aElement)
      : aElement.localeCompare(bElement);
  }
  return 0;
}
