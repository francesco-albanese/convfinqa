import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { UserMenu } from "@/components/UserMenu";
import { setMode, type ThemeMode, themeStore } from "@/theme/themeStore";

function renderUserMenu(
	props: Partial<React.ComponentProps<typeof UserMenu>> = {},
) {
	const onSignOut = props.onSignOut ?? vi.fn();
	render(
		<UserMenu
			userId={props.userId ?? "dev-user"}
			collapsed={props.collapsed ?? false}
			onSignOut={onSignOut}
		/>,
	);
	return { onSignOut };
}

async function openThemeSubmenu(user: ReturnType<typeof userEvent.setup>) {
	await user.click(screen.getByRole("button", { name: /open user menu/i }));
	await user.click(await screen.findByRole("menuitem", { name: /^theme$/i }));
}

async function selectThemeRadio(
	user: ReturnType<typeof userEvent.setup>,
	mode: ThemeMode,
) {
	await openThemeSubmenu(user);
	const radio = await screen.findByRole("menuitemradio", {
		name: new RegExp(`^${mode}$`, "i"),
	});
	// user.click on a Radix DropdownMenuRadioItem inside a SubContent portal does
	// not fire onSelect under jsdom. Focus + Enter is the reliable activation path
	// and also matches the keyboard accessibility flow.
	radio.focus();
	await user.keyboard("{Enter}");
}

describe("UserMenu", () => {
	afterEach(() => {
		setMode("system");
	});

	it("renders an avatar with the first two characters of the userId upper-cased", () => {
		renderUserMenu({ userId: "francesco" });

		expect(screen.getByText("FR")).toBeVisible();
		expect(screen.getByText("francesco")).toBeVisible();
	});

	it("opens the menu and exposes Theme and Sign out entries", async () => {
		const user = userEvent.setup();
		renderUserMenu();

		await user.click(screen.getByRole("button", { name: /open user menu/i }));

		expect(
			await screen.findByRole("menuitem", { name: /^theme$/i }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("menuitem", { name: /sign out/i }),
		).toBeInTheDocument();
	});

	it("calls onSignOut when the user selects Sign out", async () => {
		const user = userEvent.setup();
		const { onSignOut } = renderUserMenu();

		await user.click(screen.getByRole("button", { name: /open user menu/i }));
		await user.click(
			await screen.findByRole("menuitem", { name: /sign out/i }),
		);

		expect(onSignOut).toHaveBeenCalledTimes(1);
	});

	it("hides the userId label when collapsed but keeps the avatar accessible", () => {
		renderUserMenu({ collapsed: true, userId: "francesco" });

		expect(screen.queryByText("francesco")).not.toBeInTheDocument();
		expect(screen.getByText("FR")).toBeVisible();
		expect(
			screen.getByRole("button", { name: /open user menu/i }),
		).toBeInTheDocument();
	});

	it("marks the current mode as the checked radio in the Theme submenu", async () => {
		setMode("light");
		const user = userEvent.setup();
		renderUserMenu();

		await openThemeSubmenu(user);

		const lightRadio = await screen.findByRole("menuitemradio", {
			name: /light/i,
		});
		expect(lightRadio).toHaveAttribute("aria-checked", "true");
		expect(
			screen.getByRole("menuitemradio", { name: /dark/i }),
		).toHaveAttribute("aria-checked", "false");
		expect(
			screen.getByRole("menuitemradio", { name: /system/i }),
		).toHaveAttribute("aria-checked", "false");
	});

	it("updates the theme store when each radio item is selected", async () => {
		const user = userEvent.setup();
		renderUserMenu();

		await selectThemeRadio(user, "light");
		expect(themeStore.state.mode).toBe("light");

		await selectThemeRadio(user, "dark");
		expect(themeStore.state.mode).toBe("dark");

		await selectThemeRadio(user, "system");
		expect(themeStore.state.mode).toBe("system");
	});
});
