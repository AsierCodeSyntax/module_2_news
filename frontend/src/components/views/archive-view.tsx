"use client"

import { useState, useEffect } from "react"
import {
    Card,
    CardHeader,
    CardTitle,
    CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { FileText, Download, Eye, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

type View = "home" | "module" | "add-news" | "review" | "archive"

interface ArchivedBulletin {
    id: string
    fileName: string
    date: string
    fileSize: string
    url: string
}

interface ArchiveViewProps {
    onNavigate: (view: View) => void
}

export function ArchiveView({ onNavigate }: ArchiveViewProps) {
    const [bulletins, setBulletins] = useState<ArchivedBulletin[]>([])
    const [selectedBulletin, setSelectedBulletin] = useState<ArchivedBulletin | null>(null)
    const [dateFilter, setDateFilter] = useState("")
    const [isLoading, setIsLoading] = useState(true)

    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

    // Cargar los PDFs desde la API de Python al abrir la vista
    useEffect(() => {
        async function fetchArchive() {
            try {
                const response = await fetch(`${API_URL}/api/archive`)
                if (!response.ok) throw new Error("Fallo al cargar el histórico")

                const data = await response.json()

                // Mapear los datos de Python a la interfaz de React
                const formattedBulletins = data.pdfs.map((pdf: any) => ({
                    id: pdf.id,
                    fileName: pdf.filename,
                    date: pdf.date,
                    fileSize: `${pdf.size_mb} MB`,
                    url: `${API_URL}${pdf.url}` // Añadimos la URL base del backend
                }))

                setBulletins(formattedBulletins)
            } catch (error) {
                console.error("Error fetching archive:", error)
            } finally {
                setIsLoading(false)
            }
        }

        fetchArchive()
    }, [API_URL])

    const filteredBulletins = dateFilter
        ? bulletins.filter((b) => b.date <= dateFilter)
        : bulletins

    return (
        <div className="flex flex-1 flex-col">
            <header className="flex h-14 items-center gap-3 border-b border-border bg-card px-8">
                <button
                    onClick={() => onNavigate("home")}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                    Home
                </button>
                <span className="text-sm text-muted-foreground">/</span>
                <h1 className="text-sm font-medium text-foreground">Archive</h1>
            </header>

            <main className="flex-1 px-8 py-8">
                <div className="mb-6">
                    <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                        Bulletin Archive
                    </h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Browse, preview, and download previously published bulletins.
                    </p>
                </div>

                <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
                    {/* Left Column - Bulletin List */}
                    <div className="lg:col-span-2">
                        <Card className="border-border">
                            <CardHeader className="pb-3">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-sm font-medium">
                                        Published Bulletins
                                    </CardTitle>
                                    <Badge variant="secondary" className="text-xs">
                                        {filteredBulletins.length} files
                                    </Badge>
                                </div>
                                <div className="pt-2">
                                    <label
                                        htmlFor="date-filter"
                                        className="mb-1.5 block text-xs font-medium text-muted-foreground"
                                    >
                                        Filter by date (up to)
                                    </label>
                                    <Input
                                        id="date-filter"
                                        type="date"
                                        value={dateFilter}
                                        onChange={(e) => setDateFilter(e.target.value)}
                                        className="h-9 text-sm"
                                    />
                                </div>
                            </CardHeader>
                            <CardContent className="px-0 pb-0">
                                <ScrollArea className="h-[480px]">
                                    {isLoading ? (
                                        <div className="flex justify-center py-10">
                                            <Loader2 className="size-6 animate-spin text-muted-foreground" />
                                        </div>
                                    ) : (
                                        <div className="flex flex-col">
                                            {filteredBulletins.map((bulletin) => (
                                                <div
                                                    key={bulletin.id}
                                                    className={cn(
                                                        "flex items-center gap-3 border-b border-border px-6 py-3 transition-colors",
                                                        selectedBulletin?.id === bulletin.id && "bg-accent"
                                                    )}
                                                >
                                                    <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted">
                                                        <FileText className="size-4 text-muted-foreground" />
                                                    </div>
                                                    <div className="flex flex-1 flex-col gap-0.5">
                                                        <p className="text-sm font-medium text-foreground">
                                                            {bulletin.date}
                                                        </p>
                                                        <p className="text-xs text-muted-foreground">
                                                            {bulletin.fileName} &middot; {bulletin.fileSize}
                                                        </p>
                                                    </div>
                                                    <div className="flex shrink-0 items-center gap-1">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-8 px-2.5 text-xs"
                                                            onClick={() => setSelectedBulletin(bulletin)}
                                                        >
                                                            <Eye className="mr-1 size-3.5" />
                                                            View
                                                        </Button>

                                                        {/* Botón de descarga real apuntando al backend */}
                                                        <a href={bulletin.url} download target="_blank" rel="noreferrer">
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="size-8 text-muted-foreground hover:text-foreground"
                                                                aria-label={`Download ${bulletin.fileName}`}
                                                            >
                                                                <Download className="size-4" />
                                                            </Button>
                                                        </a>
                                                    </div>
                                                </div>
                                            ))}
                                            {filteredBulletins.length === 0 && !isLoading && (
                                                <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground">
                                                    <FileText className="size-8 opacity-50" />
                                                    <p className="text-sm">No bulletins found</p>
                                                    <p className="text-xs">
                                                        Try adjusting the date filter
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </ScrollArea>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Right Column - PDF Preview */}
                    <div className="lg:col-span-3">
                        <Card className="border-border">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-medium">
                                    {selectedBulletin
                                        ? selectedBulletin.fileName
                                        : "PDF Preview"}
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                {selectedBulletin ? (
                                    <div className="overflow-hidden rounded-lg border border-border">
                                        <iframe
                                            src={`${selectedBulletin.url}#toolbar=0`}
                                            title={`Preview of ${selectedBulletin.fileName}`}
                                            className="h-[520px] w-full bg-muted"
                                        />
                                    </div>
                                ) : (
                                    <div className="flex h-[520px] flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/50">
                                        <FileText className="mb-3 size-10 text-muted-foreground/50" />
                                        <p className="text-sm font-medium text-muted-foreground">
                                            Select a bulletin to preview
                                        </p>
                                        <p className="mt-1 text-xs text-muted-foreground/70">
                                            Choose a file from the list on the left
                                        </p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </main>
        </div>
    )
}