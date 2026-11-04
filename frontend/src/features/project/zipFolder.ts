/**
 * Packs a folder picked via `<input webkitdirectory>` into an uncompressed
 * (STORE) zip so it can go through the existing raw-zip upload endpoint.
 * The backend still re-validates every entry; filtering here only keeps the
 * request under the upload limit and avoids sending secrets.
 */

// Keep in sync with IGNORED_DIRECTORIES / _is_sensitive_file / limits in the backend.
const IGNORED_DIRECTORIES = new Set([
  ".git", ".hg", ".svn", ".venv", "venv", "env", ".env", "node_modules", "__pycache__",
  ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "dist", "build", ".idea", ".vscode",
]);
const MAX_FILE_BYTES = 1_048_576;
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const MAX_ENTRIES = 0xffff;

export interface ZippedFolder { zip: File; fileCount: number; skippedCount: number }

/** True when the picked folder contains at least one Python source file. */
export function hasPythonFile(files: File[]): boolean {
  return files.some((file) => {
    const path = relativePath(file);
    const name = path.split("/").pop() ?? path;
    return name.toLowerCase().endsWith(".py");
  });
}

function isSensitive(name: string): boolean {
  return name === ".env" || name.startsWith(".env.") || name.startsWith(".env-");
}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(bytes: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

const UTF8_FLAG = 0x0800;
const DOS_DATE_1980_01_01 = 0x21;

function localHeader(name: Uint8Array, crc: number, size: number): Uint8Array {
  const buf = new Uint8Array(30 + name.length);
  const v = new DataView(buf.buffer);
  v.setUint32(0, 0x04034b50, true);
  v.setUint16(4, 20, true);
  v.setUint16(6, UTF8_FLAG, true);
  v.setUint16(8, 0, true);
  v.setUint16(10, 0, true);
  v.setUint16(12, DOS_DATE_1980_01_01, true);
  v.setUint32(14, crc, true);
  v.setUint32(18, size, true);
  v.setUint32(22, size, true);
  v.setUint16(26, name.length, true);
  v.setUint16(28, 0, true);
  buf.set(name, 30);
  return buf;
}

function centralHeader(name: Uint8Array, crc: number, size: number, offset: number): Uint8Array {
  const buf = new Uint8Array(46 + name.length);
  const v = new DataView(buf.buffer);
  v.setUint32(0, 0x02014b50, true);
  v.setUint16(4, 20, true);
  v.setUint16(6, 20, true);
  v.setUint16(8, UTF8_FLAG, true);
  v.setUint16(10, 0, true);
  v.setUint16(12, 0, true);
  v.setUint16(14, DOS_DATE_1980_01_01, true);
  v.setUint32(16, crc, true);
  v.setUint32(20, size, true);
  v.setUint32(24, size, true);
  v.setUint16(28, name.length, true);
  v.setUint32(42, offset, true);
  buf.set(name, 46);
  return buf;
}

function endOfCentralDirectory(entries: number, size: number, offset: number): Uint8Array {
  const buf = new Uint8Array(22);
  const v = new DataView(buf.buffer);
  v.setUint32(0, 0x06054b50, true);
  v.setUint16(8, entries, true);
  v.setUint16(10, entries, true);
  v.setUint32(12, size, true);
  v.setUint32(16, offset, true);
  return buf;
}

function relativePath(file: File): string {
  return (file.webkitRelativePath || file.name).replace(/\\/g, "/");
}

export async function zipFolder(files: File[]): Promise<ZippedFolder> {
  if (files.length === 0) throw new Error("The selected folder is empty.");
  const rootName = relativePath(files[0]).split("/")[0] || "uploaded-project";

  const kept: File[] = [];
  let skippedCount = 0;
  for (const file of files) {
    const path = relativePath(file);
    const parts = path.split("/");
    const dirs = parts.slice(0, -1);
    const name = parts[parts.length - 1];
    if (name === ".DS_Store" || dirs.some((d) => IGNORED_DIRECTORIES.has(d)) || isSensitive(name) || file.size > MAX_FILE_BYTES) { skippedCount++; continue; }
    kept.push(file);
  }
  if (kept.length === 0) throw new Error("No uploadable files in the selected folder (everything was ignored, sensitive, or over 1 MB).");
  if (kept.length > MAX_ENTRIES) throw new Error(`Folder has too many files (${kept.length}); upload a smaller project.`);
  const payloadBytes = kept.reduce((n, f) => n + f.size, 0);
  if (payloadBytes > MAX_UPLOAD_BYTES) throw new Error("Folder exceeds the 10 MB upload limit after skipping ignored files.");

  const encoder = new TextEncoder();
  const body: Uint8Array[] = [];
  const central: Uint8Array[] = [];
  let offset = 0;
  for (const file of kept) {
    const name = encoder.encode(relativePath(file));
    const data = new Uint8Array(await file.arrayBuffer());
    const crc = crc32(data);
    const header = localHeader(name, crc, data.length);
    central.push(centralHeader(name, crc, data.length, offset));
    body.push(header, data);
    offset += header.length + data.length;
  }
  const centralSize = central.reduce((n, c) => n + c.length, 0);
  const end = endOfCentralDirectory(kept.length, centralSize, offset);

  const zip = new File([...body, ...central, end] as BlobPart[], `${rootName}.zip`, { type: "application/zip" });
  return { zip, fileCount: kept.length, skippedCount };
}
