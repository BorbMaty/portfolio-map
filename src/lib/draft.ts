/**
 * True when an MDX source's frontmatter sets `draft: true`.
 * Shared by content.config.ts (to keep drafts out of production builds) and the smoke tests, so both agree.
 * Only the frontmatter block is checked, so a `draft: true` line in a code fence in the body never counts.
 * Matches the YAML 1.2 spellings the schema's z.boolean() accepts (true/True/TRUE) and a trailing comment.
 * Pure string logic: content.config.ts runs without Node types, so no fs here.
 */
export function isDraftSource(src: string): boolean {
  const frontmatter = src.match(/^---\r?\n([\s\S]*?)\r?\n---/)?.[1] ?? '';
  return /^draft:[ \t]*true[ \t]*(#.*)?$/im.test(frontmatter);
}
