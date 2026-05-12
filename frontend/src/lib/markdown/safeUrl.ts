const ALLOWED_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

export function safeUrlTransform(url: string): string {
	if (!url) return "";
	if (/^[#?/]/.test(url)) return url;

	const match = /^([a-z][a-z0-9+.-]*):/i.exec(url);
	if (!match?.[1]) return url;

	const protocol = `${match[1].toLowerCase()}:`;
	return ALLOWED_PROTOCOLS.has(protocol) ? url : "";
}
