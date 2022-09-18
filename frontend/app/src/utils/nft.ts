export const isVideo = (url: string | null): boolean => {
  const videoExtensions = ['mp4', 'mov', 'webm', 'ogg'];
  return videoExtensions.some(
    extension => url !== null && url.endsWith(extension)
  );
};

export const isNft = (address?: string) => {
  if (!address) return false;
  return address.startsWith('_nft_');
};
