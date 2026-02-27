"use client"

import { useState } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { HomeView } from "@/components/views/home-view"
import { ModuleView } from "@/components/views/module-view"
import { AddNewsView } from "@/components/views/add-news-view"
import { ReviewView } from "@/components/views/review-view"
import { ArchiveView } from "@/components/views/archive-view"
import { SourcesView } from "@/components/views/sources-view"
import { M2ChartsView } from "@/components/views/news-module-charts"

type View = "home" | "module" | "add-news" | "review" | "archive" | "sources" | "m2-charts"

export default function Page() {
  const [currentView, setCurrentView] = useState<View>("home")

  return (
    <div className="flex h-screen bg-background">
      <AppSidebar currentView={currentView} onNavigate={setCurrentView} />
      {currentView === "home" && <HomeView onNavigate={setCurrentView} />}
      {currentView === "module" && <ModuleView onNavigate={setCurrentView} />}
      {currentView === "add-news" && (
        <AddNewsView onNavigate={setCurrentView} />
      )}
      {currentView === "review" && <ReviewView onNavigate={setCurrentView} />}
      {currentView === "archive" && <ArchiveView onNavigate={setCurrentView} />}
      {currentView === "sources" && <SourcesView onNavigate={setCurrentView} />}
      {currentView === "m2-charts" && <M2ChartsView onNavigate={setCurrentView} />}

    </div>
  )
}
