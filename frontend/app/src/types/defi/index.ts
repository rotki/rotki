import { z } from 'zod/v4';

export const ProtocolMetadataSchema = z.object({
  identifier: z.string(),
  name: z.string(),
  icon: z.string(),
  iconUrl: z.string().optional(),
});

export type ProtocolMetadata = z.infer<typeof ProtocolMetadataSchema>;

export const ProtocolMetadataArraySchema = z.array(ProtocolMetadataSchema);

export type ProtocolMetadataArray = z.infer<typeof ProtocolMetadataArraySchema>;
