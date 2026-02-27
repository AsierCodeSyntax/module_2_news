"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
    Rss,
    DownloadCloud,
    Sparkles,
    UserPlus,
    Star,
    TrendingUp,
    TrendingDown,
    Loader2
} from "lucide-react"
import {
    AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts"

interface HomeViewProps {
    onNavigate: (view: string) => void
}

function readCssVar(varName: string, fallback: string) {
    if (typeof window === "undefined") return fallback
    const v = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
    return v || fallback
}

function useResolvedChartColors() {
    const [colors, setColors] = useState(() => ({
        chart1: "#f97316", chart2: "#10b981", chart3: "#6366f1", chart4: "#eab308", chart5: "#ef4444",
        border: "rgba(0,0,0,0.15)", mutedFg: "rgba(0,0,0,0.6)",
    }))

    const recompute = React.useCallback(() => {
        const isDark = document.documentElement.classList.contains('dark')
        setColors({
            chart1: isDark ? "#fb923c" : "#f97316",
            chart2: isDark ? "#34d399" : "#10b981",
            chart3: isDark ? "#818cf8" : "#6366f1",
            chart4: isDark ? "#facc15" : "#eab308",
            chart5: isDark ? "#f87171" : "#ef4444",
            border: readCssVar("--border", "rgba(0,0,0,0.15)"),
            mutedFg: readCssVar("--muted-foreground", "rgba(0,0,0,0.6)"),
        })
    }, [])

    useEffect(() => {
        recompute()
        const obs = new MutationObserver(recompute)
        obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class", "style"] })
        return () => obs.disconnect()
    }, [recompute])

    return colors
}

// Tooltips personalizados para los gráficos
const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
        <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-md">
            <p className="text-xs font-medium text-foreground">{label}</p>
            <p className="text-sm font-semibold text-foreground">{payload[0].value} articles</p>
        </div>
    )
}

const QualityTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null
    return (
        <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-md">
            <p className="text-xs font-medium text-foreground">{payload[0].payload.topic}</p>
            <p className="text-sm font-semibold text-foreground">{Number(payload[0].value).toFixed(1)} / 10</p>
        </div>
    )
}

const PieTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null
    return (
        <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-md">
            <p className="text-xs font-medium text-foreground">{payload[0].name}</p>
            <p className="text-sm font-semibold text-foreground">{payload[0].value} articles</p>
        </div>
    )
}

export function M2ChartsView({ onNavigate }: HomeViewProps) {
    const c = useResolvedChartColors()
    const [stats, setStats] = useState<any>(null)
    const [isLoading, setIsLoading] = useState(true)

    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

    useEffect(() => {
        async function fetchStats() {
            try {
                const response = await fetch(`${API_URL}/api/dashboard/stats`)
                if (response.ok) {
                    const data = await response.json()
                    setStats(data)
                }
            } catch (error) {
                console.error("Error cargando estadísticas:", error)
            } finally {
                setIsLoading(false)
            }
        }
        fetchStats()
    }, [API_URL])

    if (isLoading) {
        return (
            <div className="flex h-full flex-1 items-center justify-center">
                <Loader2 className="size-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (!stats) return null

    // Preparar colores para el Donut Chart basado en los datos reales
    const pieColors = [c.chart1, c.chart2, c.chart3, c.chart4, c.chart5]
    const sourceDistribution = stats.source_distribution.map((item: any, index: number) => ({
        ...item,
        color: pieColors[index % pieColors.length]
    }))

    // Mapeo de colores para los topics (por si hay nuevos)
    const getTopicColor = (topic: string) => {
        const t = topic.toLowerCase()
        if (t.includes('ai')) return "bg-orange-500/10 text-orange-600 border border-orange-200"
        if (t.includes('plone')) return "bg-emerald-500/10 text-emerald-600 border border-emerald-200"
        if (t.includes('django')) return "bg-indigo-500/10 text-indigo-600 border border-indigo-200"
        return "bg-slate-500/10 text-slate-600 border border-slate-200"
    }

    return (
        <div className="flex flex-1 flex-col">
            <header className="flex h-14 items-center border-b border-border bg-card px-8">
                <h1 className="text-sm font-medium text-foreground">Dashboard</h1>
            </header>

            <main className="flex-1 overflow-y-auto px-8 py-8">
                <div className="mb-8">
                    <h2 className="text-2xl font-semibold tracking-tight text-balance text-foreground">
                        Welcome back
                    </h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Here's what your AI agents have been doing in the last 7 days.
                    </p>
                </div>

                {/* Zone 1: KPI Cards */}
                <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <Card className="border-border">
                        <CardContent className="flex items-start gap-4 p-5">
                            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-orange-500/10">
                                <Rss className="size-5 text-orange-500" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-xs font-medium text-muted-foreground">Different Sources</span>
                                <span className="mt-0.5 text-2xl font-semibold tracking-tight text-foreground">{stats.kpis.active_sources}</span>
                                <span className="mt-1 text-xs text-muted-foreground">in YAML config</span>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-border">
                        <CardContent className="flex items-start gap-4 p-5">
                            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
                                <DownloadCloud className="size-5 text-emerald-500" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-xs font-medium text-muted-foreground">Ingested Articles</span>
                                <span className="mt-0.5 text-2xl font-semibold tracking-tight text-foreground">{stats.kpis.ingested}</span>
                                <span className="mt-1 text-xs text-muted-foreground">Last 7 days</span>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-border">
                        <CardContent className="flex items-start gap-4 p-5">
                            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-yellow-500/10">
                                <Sparkles className="size-5 text-yellow-500" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-xs font-medium text-muted-foreground">High Quality (≥ 8)</span>
                                <span className="mt-0.5 text-2xl font-semibold tracking-tight text-foreground">{stats.kpis.high_quality}</span>
                                <span className="mt-1 text-xs text-muted-foreground">Last 7 days</span>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-border">
                        <CardContent className="flex items-start gap-4 p-5">
                            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10">
                                <UserPlus className="size-5 text-indigo-500" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-xs font-medium text-muted-foreground">Manual Submissions</span>
                                <span className="mt-0.5 text-2xl font-semibold tracking-tight text-foreground">{stats.kpis.manual}</span>
                                <span className="mt-1 text-xs text-muted-foreground">Last 7 days</span>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Zone 2: Main Charts */}
                <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-5">
                    {/* Ingestion Volume - 60% */}
                    <Card className="border-border lg:col-span-3">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-foreground">7-Day Ingestion Volume</CardTitle>
                        </CardHeader>
                        <CardContent className="pb-4">
                            <div className="h-[260px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={stats.ingestion_data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                                        <defs>
                                            <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="0%" stopColor={c.chart1} stopOpacity={0.3} />
                                                <stop offset="100%" stopColor={c.chart1} stopOpacity={0.02} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke={c.border} vertical={false} />
                                        <XAxis dataKey="day" tick={{ fontSize: 12, fill: c.mutedFg }} axisLine={false} tickLine={false} />
                                        <YAxis tick={{ fontSize: 12, fill: c.mutedFg }} axisLine={false} tickLine={false} />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Area type="monotone" dataKey="articles" stroke={c.chart1} strokeWidth={2} fill="url(#areaGradient)" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Quality by Topic - 40% */}
                    <Card className="border-border lg:col-span-2">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-foreground">Avg. Quality by Topic</CardTitle>
                        </CardHeader>
                        <CardContent className="pb-4">
                            <div className="h-[260px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={stats.quality_by_topic} layout="vertical" margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke={c.border} horizontal={false} />
                                        <XAxis type="number" domain={[0, 10]} tick={{ fontSize: 12, fill: c.mutedFg }} axisLine={false} tickLine={false} />
                                        <YAxis type="category" dataKey="topic" tick={{ fontSize: 12, fill: c.mutedFg }} axisLine={false} tickLine={false} width={70} />
                                        <Tooltip content={<QualityTooltip />} />
                                        <Bar dataKey="score" fill={c.chart2} radius={[0, 4, 4, 0]} barSize={20} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Zone 3: Details */}
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
                    {/* Source Distribution - 40% */}
                    <Card className="border-border lg:col-span-2">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-foreground">Source Distribution</CardTitle>
                        </CardHeader>
                        <CardContent className="pb-4">
                            <div className="flex h-[240px] items-center justify-center">
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Tooltip content={<PieTooltip />} />
                                        <Pie data={sourceDistribution} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={3} dataKey="value" strokeWidth={0}>
                                            {sourceDistribution.map((entry: any) => (
                                                <Cell key={entry.name} fill={entry.color} />
                                            ))}
                                        </Pie>
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="flex flex-wrap items-center justify-center gap-4">
                                {sourceDistribution.map((entry: any) => (
                                    <div key={entry.name} className="flex items-center gap-2">
                                        <div className="size-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
                                        <span className="text-xs text-muted-foreground">{entry.name} ({entry.value})</span>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Top Articles - 60% */}
                    <Card className="border-border lg:col-span-3">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-foreground">Top Articles (Waiting for Bulletin)</CardTitle>
                        </CardHeader>
                        <CardContent className="pb-4">
                            {stats.top_articles.length === 0 ? (
                                <div className="flex h-full items-center justify-center py-10 text-muted-foreground">
                                    No articles found. Run the Scout!
                                </div>
                            ) : (
                                <div className="flex flex-col">
                                    {stats.top_articles.map((article: any, index: number) => (
                                        <div key={article.id} className={`flex items-center gap-4 py-4 ${index < stats.top_articles.length - 1 ? "border-b border-border" : ""}`}>
                                            <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                                                {index + 1}
                                            </div>
                                            <div className="flex min-w-0 flex-1 flex-col gap-1">
                                                <span className="truncate text-sm font-medium text-foreground">{article.title}</span>
                                                <Badge variant="secondary" className={`w-fit text-[10px] ${getTopicColor(article.topic)}`}>
                                                    {article.topic}
                                                </Badge>
                                            </div>
                                            <div className="flex shrink-0 items-center gap-1.5">
                                                <Star className="size-3.5 fill-yellow-500 text-yellow-500" />
                                                <span className="text-sm font-semibold text-foreground">{article.score.toFixed(1)}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </main>
        </div>
    )
}