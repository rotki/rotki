import { z } from 'zod';
import { AssetPrice } from '@/services/assets/types';

const NonFungiblePrice = AssetPrice.merge(
  z.object({ name: z.string().nullable() })
);
export type NonFungiblePrice = z.infer<typeof NonFungiblePrice>;
