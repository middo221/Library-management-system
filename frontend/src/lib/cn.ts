/** Minimal class joiner — no runtime dependency for something this small. */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ')
}
