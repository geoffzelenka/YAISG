import type { Item, Selector } from '../../api/content'

export function matches(item: Item, selector: Selector): boolean {
  return selector.item !== undefined
    ? selector.item === item.id
    : item.classes.includes(selector.class) &&
        (selector.tier === undefined || item.tier === selector.tier)
}
export function selectorLabel(selector: Selector): string {
  return (
    selector.item ??
    `${selector.class}${selector.tier === undefined ? '' : ` tier ${selector.tier}`}`
  )
}
export function coverDays(stockMilli: number, perDay: number): string {
  return perDay > 0
    ? `${(stockMilli / 1000 / perDay).toFixed(2)} days`
    : 'No upkeep'
}
