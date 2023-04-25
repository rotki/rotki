import { createBlockie } from '@/utils/blockie';

describe('composables::accounts/blockie', () => {
  const { cache, getBlockie, isPending } = useBlockie();
  let firstBlockie = '';
  const address = '0x790b4086d106eafd913e71843aed987efe291c92';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create new blockie', async () => {
    firstBlockie = getBlockie(address);
    const pending = isPending(address);
    await until(pending).toBe(false);
    expect(createBlockie).toHaveBeenCalled();
    firstBlockie = getBlockie(address);
  });

  it('should not create new blockie', () => {
    const addressInUppercase = '0x790B4086D106EAFD913E71843AED987EFE291C92';
    const newBlockie = getBlockie(addressInUppercase);
    expect(createBlockie).not.toHaveBeenCalled();
    expect(firstBlockie).toEqual(newBlockie);
  });

  it('should keep caching blockie, not remove the earlier data, after cache limit is reached but called in the relatively same time', async () => {
    expect(Object.keys(get(cache)).length).toEqual(1);
    expect(get(cache)[address]).toBeTruthy();
    for (let i = 0; i < 200; i++) {
      getBlockie(i.toString());
    }
    const pending = isPending('199');
    await until(pending).toBe(false);
    expect(Object.keys(get(cache)).length).toEqual(201);
    expect(get(cache)[address]).toBeTruthy();
  });

  it('should stop caching blockie after cache limit is reached', async () => {
    const date = new Date(Date.now() + 10000);
    vi.setSystemTime(date);
    expect(Object.keys(get(cache)).length).toEqual(201);
    expect(get(cache)[address]).toBeTruthy();
    for (let i = 200; i < 400; i++) {
      getBlockie(i.toString());
    }
    const pending = isPending('399');

    await until(pending).toBe(false);
    expect(Object.keys(get(cache)).length).toEqual(200);
    expect(get(cache)[address]).toBeFalsy();
  });
});
