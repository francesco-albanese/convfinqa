import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

type UserMenuProps = {
	userId: string;
	collapsed: boolean;
	onSignOut: () => void;
};

function initialsFor(userId: string): string {
	return userId.slice(0, 2).toUpperCase();
}

export function UserMenu({ userId, collapsed, onSignOut }: UserMenuProps) {
	const initials = initialsFor(userId);

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
					<span className="min-w-0 truncate text-left text-sm">{userId}</span>
				)}
			</DropdownMenuTrigger>
			<DropdownMenuContent align="start" side="top" className="w-56">
				<DropdownMenuLabel className="truncate">{userId}</DropdownMenuLabel>
				<DropdownMenuSeparator />
				<DropdownMenuItem disabled aria-disabled="true">
					Theme: dark/light
				</DropdownMenuItem>
				<DropdownMenuSeparator />
				<DropdownMenuItem onSelect={onSignOut}>Sign out</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
