"use client"

import { useState, useEffect } from "react"
import {
    Card,
    CardHeader,
    CardTitle,
    CardDescription,
    CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    CheckCircle,
    XCircle,
    RefreshCw,
    Trash2,
    Plus,
    Loader2,
    Rss,
    Clock,
    ExternalLink,
} from "lucide-react"
import { cn } from "@/lib/utils"

type View = "home" | "module" | "add-news" | "review" | "archive" | "sources"

interface SourcesViewProps {
    onNavigate: (view: string) => void
}

interface RssFeed {
    id: string
    name: string
    url: string
    topic: string
    status: "valid" | "error" | "pending"
    lastChecked: string
}

const topicColors: Record<string, string> = {
    plone: "bg-[oklch(0.55_0.15_220)] text-[oklch(0.985_0_0)]",
    django: "bg-[oklch(0.52_0.17_152)] text-[oklch(0.985_0_0)]",
    ai: "bg-[oklch(0.55_0.2_280)] text-[oklch(0.985_0_0)]",
}

const statusConfig: Record<
    string,
    { label: string; icon: typeof CheckCircle; className: string }
> = {
    valid: {
        label: "Valid",
        icon: CheckCircle,
        className:
            "bg-[oklch(0.52_0.17_152/0.12)] text-[oklch(0.42_0.17_152)] border-[oklch(0.52_0.17_152/0.2)]",
    },
    error: {
        label: "Error",
        icon: XCircle,
        className:
            "bg-destructive/10 text-destructive border-destructive/20",
    },
    pending: {
        label: "Pending",
        icon: Clock,
        className: "bg-muted text-muted-foreground border-border",
    },
}

export function SourcesView({ onNavigate }: SourcesViewProps) {
    const [feeds, setFeeds] = useState<RssFeed[]>([])
    const [feedName, setFeedName] = useState("")
    const [feedUrl, setFeedUrl] = useState("")
    const [feedTopic, setFeedTopic] = useState("")

    const [isAdding, setIsAdding] = useState(false)
    const [isLoadingInitial, setIsLoadingInitial] = useState(true)
    const [validatingAll, setValidatingAll] = useState(false)
    const [validatingIds, setValidatingIds] = useState<Set<string>>(new Set())

    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

    // 1. Cargar las fuentes al iniciar
    const fetchSources = async () => {
        try {
            const response = await fetch(`${API_URL}/api/sources`)
            if (response.ok) {
                const data = await response.json()
                const formattedSources = data.sources.map((s: any) => ({
                    ...s,
                    lastChecked: "Just loaded"
                }))
                setFeeds(formattedSources)
            }
        } catch (error) {
            console.error("Error fetching sources:", error)
        } finally {
            setIsLoadingInitial(false)
        }
    }

    useEffect(() => {
        fetchSources()
    }, [])

    // 2. Añadir y validar un nuevo RSS
    async function handleAddFeed(e: React.FormEvent) {
        e.preventDefault()
        if (!feedUrl || !feedTopic) return

        setIsAdding(true)
        try {
            const response = await fetch(`${API_URL}/api/sources`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: feedName,
                    url: feedUrl,
                    topic: feedTopic.toLowerCase()
                })
            })

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(errorData.detail || "Error validando el RSS")
            }

            alert("✅ Fuente añadida correctamente al archivo YAML.")
            setFeedUrl("")
            setFeedTopic("")
            await fetchSources() // Recargar la lista

        } catch (error: any) {
            alert(`❌ Error: ${error.message}`)
        } finally {
            setIsAdding(false)
        }
    }

    // 3. Borrar un RSS
    async function handleDelete(topic: string, url: string) {
        if (!confirm(`¿Seguro que quieres borrar este RSS de ${topic}?`)) return

        try {
            const response = await fetch(
                `${API_URL}/api/sources?topic=${encodeURIComponent(topic)}&url=${encodeURIComponent(url)}`,
                { method: "DELETE" }
            )

            if (response.ok) {
                await fetchSources() // Recargar la lista
            } else {
                alert("❌ Error al borrar el RSS")
            }
        } catch (error) {
            console.error("Error deleting:", error)
        }
    }

    // 4. Validar un solo RSS
    async function handleValidate(feed: RssFeed) {
        setValidatingIds((prev) => new Set(prev).add(feed.id))

        try {
            const response = await fetch(`${API_URL}/api/sources/validate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: feed.name, url: feed.url, topic: feed.topic })
            })

            const status = response.ok ? "valid" : "error"

            setFeeds((prev) =>
                prev.map((f) =>
                    f.id === feed.id ? { ...f, status: status, lastChecked: "Just now" } : f
                )
            )
        } catch (error) {
            setFeeds((prev) =>
                prev.map((f) =>
                    f.id === feed.id ? { ...f, status: "error", lastChecked: "Just now" } : f
                )
            )
        } finally {
            setValidatingIds((prev) => {
                const next = new Set(prev)
                next.delete(feed.id)
                return next
            })
        }
    }

    // 5. Validar todos de golpe
    async function handleValidateAll() {
        setValidatingAll(true)
        const allIds = new Set(feeds.map((f) => f.id))
        setValidatingIds(allIds)

        // Validamos todos en paralelo
        await Promise.allSettled(feeds.map(feed => handleValidate(feed)))

        setValidatingAll(false)
    }

    const validCount = feeds.filter((f) => f.status === "valid").length
    const errorCount = feeds.filter((f) => f.status === "error").length

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
                <h1 className="text-sm font-medium text-foreground">RSS Sources</h1>
            </header>

            <main className="flex-1 overflow-y-auto px-8 py-8">
                <div className="mb-8">
                    <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                        RSS Sources
                    </h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Manage your RSS feeds for automated news ingestion and monitoring.
                    </p>
                </div>

                {/* Add New Feed Card */}
                <Card className="mb-6 border-border">
                    <CardHeader className="pb-4">
                        <CardTitle className="text-base">Add New Feed</CardTitle>
                        <CardDescription>
                            Enter the feed details below. The URL will be validated automatically before saving.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleAddFeed} className="flex flex-col gap-4 lg:flex-row lg:items-end">
                            {/* EL CAMPO RECUPERADO: Feed Name */}
                            <div className="flex flex-1 flex-col gap-2">
                                <Label htmlFor="feed-name" className="text-sm font-medium text-foreground">
                                    Feed Name
                                </Label>
                                <Input
                                    id="feed-name"
                                    placeholder="e.g. Plone Community"
                                    value={feedName}
                                    onChange={(e) => setFeedName(e.target.value)}
                                    required
                                />
                            </div>

                            <div className="flex flex-[2] flex-col gap-2">
                                <Label htmlFor="feed-url" className="text-sm font-medium text-foreground">
                                    RSS URL
                                </Label>
                                <Input
                                    id="feed-url"
                                    type="url"
                                    placeholder="https://example.com/rss"
                                    value={feedUrl}
                                    onChange={(e) => setFeedUrl(e.target.value)}
                                    required
                                />
                            </div>

                            <div className="flex w-full flex-col gap-2 lg:w-40">
                                <Label htmlFor="feed-topic" className="text-sm font-medium text-foreground">
                                    Topic
                                </Label>
                                <Select value={feedTopic} onValueChange={setFeedTopic} required>
                                    <SelectTrigger className="w-full" id="feed-topic">
                                        <SelectValue placeholder="Topic" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="plone">Plone</SelectItem>
                                        <SelectItem value="django">Django</SelectItem>
                                        <SelectItem value="ai">AI</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <Button
                                type="submit"
                                disabled={!feedName || !feedUrl || !feedTopic || isAdding}
                                className="h-9 shrink-0 lg:w-auto"
                            >
                                {isAdding ? (
                                    <>
                                        <Loader2 className="size-4 mr-2 animate-spin" />
                                        Validating...
                                    </>
                                ) : (
                                    <>
                                        <Plus className="size-4 mr-2" />
                                        Add & Validate
                                    </>
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {/* Sources List Card */}
                <Card className="border-border">
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <CardTitle className="text-base">All Sources</CardTitle>
                                <div className="flex items-center gap-2">
                                    <Badge variant="secondary" className="text-xs">
                                        {feeds.length} feeds
                                    </Badge>
                                    {validCount > 0 && (
                                        <Badge
                                            className={cn(
                                                "border text-xs",
                                                statusConfig.valid.className
                                            )}
                                        >
                                            {validCount} valid
                                        </Badge>
                                    )}
                                    {errorCount > 0 && (
                                        <Badge
                                            className={cn(
                                                "border text-xs",
                                                statusConfig.error.className
                                            )}
                                        >
                                            {errorCount} error
                                        </Badge>
                                    )}
                                </div>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleValidateAll}
                                disabled={validatingAll || feeds.length === 0}
                            >
                                {validatingAll ? (
                                    <>
                                        <Loader2 className="size-3.5 mr-2 animate-spin" />
                                        Validating...
                                    </>
                                ) : (
                                    <>
                                        <RefreshCw className="size-3.5 mr-2" />
                                        Validate All
                                    </>
                                )}
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent className="px-0 pb-0">
                        <div className="grid grid-cols-[1fr_100px_90px_80px] items-center gap-4 border-b border-border bg-muted/40 px-6 py-2.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                            <span>Feed</span>
                            <span>Topic</span>
                            <span>Status</span>
                            <span className="text-right">Actions</span>
                        </div>

                        <ScrollArea className="h-[400px]">
                            {isLoadingInitial ? (
                                <div className="flex justify-center py-10">
                                    <Loader2 className="size-6 animate-spin text-muted-foreground" />
                                </div>
                            ) : (
                                <div className="flex flex-col">
                                    {feeds.map((feed) => {
                                        const status = statusConfig[feed.status]
                                        const StatusIcon = status.icon
                                        const isValidating = validatingIds.has(feed.id)

                                        return (
                                            <div
                                                key={feed.id}
                                                className="grid grid-cols-[1fr_100px_90px_80px] items-center gap-4 border-b border-border px-6 py-3.5 transition-colors hover:bg-accent/30"
                                            >
                                                {/* Name & URL */}
                                                <div className="flex min-w-0 flex-col gap-0.5">
                                                    <div className="flex items-center gap-2">
                                                        <Rss className="size-3.5 shrink-0 text-muted-foreground" />
                                                        <span className="truncate text-sm font-medium text-foreground">
                                                            {feed.name}
                                                        </span>
                                                    </div>
                                                    <a
                                                        href={feed.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="flex items-center gap-1 truncate text-xs text-muted-foreground transition-colors hover:text-foreground"
                                                    >
                                                        <span className="truncate">{feed.url}</span>
                                                        <ExternalLink className="size-2.5 shrink-0" />
                                                    </a>
                                                    <span className="text-[11px] text-muted-foreground/70">
                                                        Checked: {feed.lastChecked}
                                                    </span>
                                                </div>

                                                {/* Topic */}
                                                <div>
                                                    <Badge
                                                        className={cn(
                                                            "border-0 text-[10px] font-semibold uppercase",
                                                            topicColors[feed.topic.toLowerCase()] ?? ""
                                                        )}
                                                    >
                                                        {feed.topic}
                                                    </Badge>
                                                </div>

                                                {/* Status */}
                                                <div>
                                                    {isValidating ? (
                                                        <Badge
                                                            variant="secondary"
                                                            className="gap-1 border border-border text-xs"
                                                        >
                                                            <Loader2 className="size-3 animate-spin" />
                                                            ...
                                                        </Badge>
                                                    ) : (
                                                        <Badge
                                                            className={cn(
                                                                "gap-1 border text-xs",
                                                                status.className
                                                            )}
                                                        >
                                                            <StatusIcon className="size-3" />
                                                            {status.label}
                                                        </Badge>
                                                    )}
                                                </div>

                                                {/* Actions */}
                                                <div className="flex items-center justify-end gap-1">
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="size-8 text-muted-foreground hover:text-foreground"
                                                        onClick={() => handleValidate(feed)}
                                                        disabled={isValidating}
                                                        aria-label={`Validate ${feed.name}`}
                                                    >
                                                        <RefreshCw
                                                            className={cn(
                                                                "size-3.5",
                                                                isValidating && "animate-spin"
                                                            )}
                                                        />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="size-8 text-muted-foreground hover:text-destructive"
                                                        onClick={() => handleDelete(feed.topic, feed.url)}
                                                        aria-label={`Delete ${feed.name}`}
                                                    >
                                                        <Trash2 className="size-3.5" />
                                                    </Button>
                                                </div>
                                            </div>
                                        )
                                    })}

                                    {feeds.length === 0 && (
                                        <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground">
                                            <Rss className="size-8" />
                                            <p className="text-sm">No RSS sources configured</p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </ScrollArea>
                    </CardContent>
                </Card>
            </main>
        </div>
    )
}