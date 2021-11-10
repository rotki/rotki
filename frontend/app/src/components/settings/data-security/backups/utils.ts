import { Ref } from '@vue/composition-api';
import { UserDbBackup } from '@/services/backup/types';

export const getFilepath = (db: UserDbBackup, directory: Ref<string>) => {
  const file = `${db.time}_rotkehlchen_db_v${db.version}.backup`;
  return `${directory.value}${file}`;
};
