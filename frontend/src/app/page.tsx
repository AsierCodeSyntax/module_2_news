"use client"

import { useState } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { HomeView } from "@/components/views/home-view"
import { ModuleView } from "@/components/views/module-view"
import { AddNewsView } from "@/components/views/add-news-view"
import { ReviewView } from "@/components/views/review-view"

type View = "home" | "module" | "add-news" | "review"

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
    </div>
  )
}
