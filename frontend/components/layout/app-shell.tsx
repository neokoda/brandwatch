import { Sidebar } from "./sidebar";

interface AppShellProps {
  children: React.ReactNode;
  accountName?: string;
}

export function AppShell({ children, accountName }: AppShellProps) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <Sidebar accountName={accountName} />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
