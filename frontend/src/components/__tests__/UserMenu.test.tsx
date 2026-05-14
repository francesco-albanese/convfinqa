import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UserMenu } from "@/components/UserMenu";

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

describe("UserMenu", () => {
	it("renders an avatar with the first two characters of the userId upper-cased", () => {
		renderUserMenu({ userId: "francesco" });

		expect(screen.getByText("FR")).toBeVisible();
		expect(screen.getByText("francesco")).toBeVisible();
	});

	it("opens the menu and shows Sign out + a disabled theme placeholder", async () => {
		const user = userEvent.setup();
		renderUserMenu();

		await user.click(screen.getByRole("button", { name: /open user menu/i }));

		const themeItem = await screen.findByRole("menuitem", {
			name: /theme: dark\/light/i,
		});
		expect(themeItem).toHaveAttribute("aria-disabled", "true");

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
});
