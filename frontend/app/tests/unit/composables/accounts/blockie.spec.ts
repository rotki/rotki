import { useBlockie } from '@/composables/accounts/blockie';

describe('accounts/blockie', () => {
  const { cache, getBlockie } = useBlockie();
  let firstBlockie = '';
  const address = '0x790b4086d106eafd913e71843aed987efe291c92';

  beforeAll(() => {
    vi.clearAllMocks();
  });

  const mockCanvasDataUrl = (address: string) => {
    const canvas = document.createElement('canvas');
    canvas.toDataURL = () => `${address.toLowerCase()}face`;

    vi.spyOn(document, 'createElement').mockReturnValue(canvas);
  };

  it('should create new blockie', () => {
    mockCanvasDataUrl(address);
    firstBlockie = getBlockie(address);
    expect(document.createElement).toHaveBeenCalledOnce();
  });

  it('should not create new blockie', () => {
    const addressInUppercase = '0x790B4086D106EAFD913E71843AED987EFE291C92';
    mockCanvasDataUrl(addressInUppercase);
    const newBlockie = getBlockie(addressInUppercase);
    expect(document.createElement).not.toHaveBeenCalledOnce();
    expect(firstBlockie).toEqual(newBlockie);
  });

  it('should stop caching blockie after cache limit is reached', () => {
    expect(cache.size).toEqual(1);
    expect(cache.has(address)).toBeTruthy();
    for (let i = 0; i < 100; i++) {
      getBlockie(i.toString());
    }
    expect(cache.size).toEqual(100);
    expect(cache.has(address)).toBeFalsy();
  });
});
