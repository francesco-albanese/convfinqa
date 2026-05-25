import { LaptopIcon, MoonIcon, SunIcon } from "lucide-react";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuSeparator,
	DropdownMenuSub,
	DropdownMenuSubContent,
	DropdownMenuSubTrigger,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { isThemeMode } from "@/theme/resolveInitialTheme";
import { setMode, useThemeMode } from "@/theme/themeStore";

type UserMenuProps = {
	userId: string;
	email: string | null;
	collapsed: boolean;
	onSignOut: () => void;
};

function initialsFor(label: string): string {
	return label.slice(0, 2).toUpperCase();
}

export function UserMenu({
	userId,
	email,
	collapsed,
	onSignOut,
}: UserMenuProps) {
	const displayName = email ?? userId;
	const initials = initialsFor(displayName);
	const themeMode = useThemeMode();

	return (
		<DropdownMenu>
			<DropdownMenuTrigger
				aria-label="Open user menu"
				data-testid="user-menu-trigger"
				className={cn(
					"flex items-center gap-2 rounded-md text-foreground text-sm hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
					collapsed
						? "h-9 w-9 justify-center self-center"
						: "h-9 w-full justify-start px-2",
				)}
			>
				<span
					aria-hidden="true"
					className="inline-flex size-7 items-center justify-center rounded-full bg-secondary font-medium text-foreground text-xs"
				>
					{initials}
				</span>
				{!collapsed && (
					<span className="min-w-0 truncate text-left text-sm">
						{displayName}
					</span>
				)}
			</DropdownMenuTrigger>
			<DropdownMenuContent align="start" side="top" className="w-56">
				<DropdownMenuLabel className="min-w-0">
					<span className="block truncate">{displayName}</span>
					{email ? (
						<span className="block truncate font-normal text-muted-foreground">
							{userId}
						</span>
					) : null}
				</DropdownMenuLabel>
				<DropdownMenuSeparator />
				<DropdownMenuSub>
					<DropdownMenuSubTrigger>Theme</DropdownMenuSubTrigger>
					<DropdownMenuSubContent>
						<DropdownMenuRadioGroup
							value={themeMode}
							onValueChange={(value) => {
								if (isThemeMode(value)) setMode(value);
							}}
						>
							<DropdownMenuRadioItem value="system">
								<LaptopIcon />
								System
							</DropdownMenuRadioItem>
							<DropdownMenuRadioItem value="light">
								<SunIcon />
								Light
							</DropdownMenuRadioItem>
							<DropdownMenuRadioItem value="dark">
								<MoonIcon />
								Dark
							</DropdownMenuRadioItem>
						</DropdownMenuRadioGroup>
					</DropdownMenuSubContent>
				</DropdownMenuSub>
				<DropdownMenuSeparator />
				<DropdownMenuItem onSelect={onSignOut}>Sign out</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
