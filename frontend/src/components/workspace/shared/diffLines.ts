export function addedLinesFromDiff(diff: string): Set<number> {
  const added = new Set<number>();
  let newLine = 0;
  for (const line of diff.split("\n")) {
    const hunk = line.match(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (hunk) { newLine = Number(hunk[1]); continue; }
    if (line.startsWith("+") && !line.startsWith("+++")) { added.add(newLine); newLine += 1; }
    else if (line.startsWith("-") && !line.startsWith("---")) { /* removed line: new-file line does not advance */ }
    else if (!line.startsWith("\\")) { newLine += 1; }
  }
  return added;
}
