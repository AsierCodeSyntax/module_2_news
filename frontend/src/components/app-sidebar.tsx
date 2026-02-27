"use client"

import { cn } from "@/lib/utils"
import {
  Home,
  Newspaper,
  PlusCircle,
  FileText,
  Archive,
  Settings,
  Eye,
  Rss,
} from "lucide-react"

type View = "home" | "module" | "add-news" | "review" | "archive" | "sources"

interface AppSidebarProps {
  currentView: View
  onNavigate: (view: View) => void
}

const navItems = [
  { id: "home" as View, label: "Home", icon: Home },
  { id: "module" as View, label: "News Bulletin", icon: Newspaper },
  { id: "add-news" as View, label: "Add News", icon: PlusCircle },
  { id: "review" as View, label: "Review Bulletin", icon: Eye },
  { id: "archive" as View, label: "Archive", icon: Archive },
  { id: "sources" as View, label: "RSS Sources", icon: Rss },
  { id: "m2-charts" as View, label: "Module 2 Charts", icon: FileText },


]

export function AppSidebar({ currentView, onNavigate }: AppSidebarProps) {
  return (
    <aside className="flex h-screen w-64 flex-col border-r border-border bg-card">
      <div className="flex h-14 items-center gap-2 border-b border-border px-5">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary">
          <Eye className="size-4 text-primary-foreground" />
        </div>
        <span className="text-sm font-semibold tracking-tight text-foreground">
          Zaintza Teknologikoa
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
        <span className="mb-2 px-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Navigation
        </span>
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = currentView === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </button>
          )
        })}
      </nav>

      <div className="border-t border-border px-3 py-4">
        <button className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
          <Settings className="size-4" />
          Settings
        </button>
      </div>
    </aside>
  )
}
