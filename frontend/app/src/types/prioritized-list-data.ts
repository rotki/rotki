export class PrioritizedListData {
  constructor(private itemData: Array<PrioritizedListItemData>) {}

  itemIdsNotIn(itemIds: string[]): string[] {
    return this.itemData
      .filter(item => !itemIds.includes(item.identifier))
      .map(itemData => itemData.identifier);
  }

  itemDataForId(id: string): PrioritizedListItemData | undefined {
    return this.itemData.find(item => item.identifier === id);
  }
}

export class PrioritizedListItemData {
  public identifier: string = '';
  public icon?: string;
  public extraDisplaySize?: string; // may be a string specifying pixels e.g. 12px
}
