import { z } from 'zod/v4';

const GlobalDbVersion = z.object({
  globaldbAssetsVersion: z.number(),
  globaldbSchemaVersion: z.number(),
});
const UserDbInfo = z.object({
  filepath: z.string(),
  size: z.number(),
  version: z.number(),
});
const UserDbBackup = z.object({
  size: z.number(),
  time: z.number(),
  version: z.number(),
});

export type UserDbBackup = z.infer<typeof UserDbBackup>;

export type UserDbBackupWithId = UserDbBackup & { id: number };

const UserDb = z.object({
  backups: z.array(UserDbBackup),
  info: UserDbInfo,
});

export const DatabaseInfoSchema = z.object({
  globaldb: GlobalDbVersion,
  userdb: UserDb,
});

export type DatabaseInfo = z.infer<typeof DatabaseInfoSchema>;

export const DatabaseInfoResponse = z.object({
  message: z.string(),
  result: DatabaseInfoSchema,
});

export type DatabaseInfoResponse = z.infer<typeof DatabaseInfoResponse>;

export const CreateDatabaseResponse = z.object({
  message: z.string(),
  result: z.string(),
});

export type CreateDatabaseResponse = z.infer<typeof CreateDatabaseResponse>;

export const DeleteDatabaseResponse = z.object({
  message: z.string(),
  result: z.boolean(),
});

export type DeleteDatabaseResponse = z.infer<typeof DeleteDatabaseResponse>;
