import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { EXTERNAL_API_KEY_SERVICES } from '@/modules/settings/api-keys/external/external-api-key-services';

const SERVICE_IMAGES = join('public', 'assets', 'images', 'services');

describe('external-api-key-services', () => {
  it('should list every service under the name its key is saved with', () => {
    const mislabelled = Object.entries(EXTERNAL_API_KEY_SERVICES)
      .filter(([key, service]) => service.name !== key)
      .map(([key]) => key);

    expect(mislabelled).toStrictEqual([]);
  });

  it('should give every service an image the app ships', () => {
    const missing = Object.values(EXTERNAL_API_KEY_SERVICES)
      .map(service => service.image)
      .filter(image => !existsSync(join(SERVICE_IMAGES, image)));

    expect(missing).toStrictEqual([]);
  });
});
