import type { LocationQuery } from '@/types/route';

export function toUriEncoded(queryParams: LocationQuery): string {
  return encodeURIComponent(
    Object.entries(queryParams).map(([key, value]) => `${key}=${value?.toString()}`).join('&'),
  );
}

export function fromUriEncoded(queryString: string): LocationQuery {
  const uriDecodedString = decodeURIComponent(queryString);
  const locationQuery: LocationQuery = {};
  const searchParams = new URLSearchParams(uriDecodedString);
  searchParams.forEach((value, key) => {
    locationQuery[key] = value;
  });
  return locationQuery;
}
