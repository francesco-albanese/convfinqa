import { afterEach, describe, expect, it } from "vitest";
import {
	closeSidebarDrawer,
	createResponsiveStore,
	openSidebarDrawer,
	responsiveStore,
	toggleSidebarDrawer,
} from "@/lib/ui/responsiveStore";

describe("responsiveStore", () => {
	afterEach(() => {
		closeSidebarDrawer();
	});

	it("defaults to drawer closed on a fresh store", () => {
		const store = createResponsiveStore();
		expect(store.state.drawerOpen).toBe(false);
	});

	it("openSidebarDrawer marks the drawer as open", () => {
		openSidebarDrawer();
		expect(responsiveStore.state.drawerOpen).toBe(true);
	});

	it("closeSidebarDrawer marks the drawer as closed after opening", () => {
		openSidebarDrawer();
		closeSidebarDrawer();
		expect(responsiveStore.state.drawerOpen).toBe(false);
	});

	it("toggleSidebarDrawer flips the drawer state", () => {
		toggleSidebarDrawer();
		expect(responsiveStore.state.drawerOpen).toBe(true);
		toggleSidebarDrawer();
		expect(responsiveStore.state.drawerOpen).toBe(false);
	});
});
