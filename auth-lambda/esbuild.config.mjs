import { execSync } from "node:child_process"
import { mkdirSync, readdirSync } from "node:fs"
import { basename, extname, join } from "node:path"
import * as esbuild from "esbuild"

const HANDLERS_DIR = "src/handlers"
const OUT_DIR = "dist"

mkdirSync(OUT_DIR, { recursive: true })

const entries = readdirSync(HANDLERS_DIR)
	.filter((f) => f.endsWith(".ts"))
	.map((f) => join(HANDLERS_DIR, f))

if (entries.length === 0) {
	console.log("No handlers found in src/handlers/ — nothing to build.")
	process.exit(0)
}

await esbuild.build({
	entryPoints: entries,
	bundle: true,
	platform: "node",
	target: "node22",
	format: "esm",
	outdir: OUT_DIR,
	outExtension: { ".js": ".mjs" },
	external: ["@aws-sdk/*"],
	sourcemap: false,
	minify: false,
	logLevel: "info",
})

for (const entry of entries) {
	const name = basename(entry, extname(entry))
	execSync(`zip -j ${name}.zip ${name}.mjs`, {
		cwd: OUT_DIR,
		stdio: "inherit",
	})
	console.log(`→ ${OUT_DIR}/${name}.zip`)
}
