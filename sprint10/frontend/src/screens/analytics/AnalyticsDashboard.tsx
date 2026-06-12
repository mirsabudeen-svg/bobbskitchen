/**
 * frontend/src/screens/analytics/AnalyticsDashboard.tsx
 *
 * Sprint 10 — /analytics route
 * PIN-protected (reuses StaffPinGate). Four panels:
 *   1. Today Live — real-time order + funnel counts
 *   2. Trend — 14-day daily chart (orders, revenue)
 *   3. Product Intelligence — style performance, size/colour, reprints
 *   4. Operational — hourly heatmap, latency, funnel conversion
 *
 * Uses recharts for all charts.
 * No external analytics SDK — all data from the BOBB backend.
 */

import { useEffect, useState, useCallback } from "react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend,
} from "recharts";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface TodayData {
  date: string;
  sessions_started: number;
  stories_submitted: number;
  orders_placed: number;
  orders_collected: number;
  revenue_paise: number;
  reprints: number;
  whatsapp_sent: number;
  orders_by_hour: number[];
  avg_order_to_ready_ms: number | null;
  funnel: {
    sessions: number;
    stories: number;
    selections: number;
    orders: number;
    collected: number;
  };
}

interface DailySummary {
  date: string;
  orders_placed: number;
  revenue_paise: number;
  sessions_started: number;
  story_to_order_rate: number;
  avg_order_to_ready_ms: number | null;
  p95_order_to_ready_ms: number | null;
  reprints: number;
  variants_failed: number;
}

interface StyleData {
  style: string;
  generated: number;
  selected: number;
  selection_rate: number;
}

interface ProductData {
  date_range: { start: string; end: string };
  styles: StyleData[];
  colors: { color: string; count: number }[];
  products: { product_size: string; count: number }[];
  reprint_analysis: Record<string, { orders: number; reprints: number; reprint_rate: number }>;
}

interface FunnelData {
  totals: { sessions: number; stories: number; orders: number; collected: number };
  drop_off: Record<string, number | null>;
  conversion_rates: Record<string, number>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Colour palette — BOBB industrial aesthetic
// ─────────────────────────────────────────────────────────────────────────────

const COLORS = {
  cyan:    "#00E5FF",
  amber:   "#FFB300",
  green:   "#00E676",
  red:     "#FF1744",
  grey:    "#616161",
  surface: "#1A1A1A",
  border:  "#2A2A2A",
};

const BAR_COLORS = [COLORS.cyan, COLORS.amber, COLORS.green, "#B388FF", "#FF80AB"];

// ─────────────────────────────────────────────────────────────────────────────
// Formatters
// ─────────────────────────────────────────────────────────────────────────────

const formatRupees = (paise: number) =>
  `₹${(paise / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

const formatMs = (ms: number | null) =>
  ms == null ? "—" : ms < 60000 ? `${(ms / 1000).toFixed(1)}s` : `${(ms / 60000).toFixed(1)}m`;

const formatPct = (v: number | null) =>
  v == null ? "—" : `${(v * 100).toFixed(1)}%`;

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color = COLORS.cyan }: {
  label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="stat-card" style={{ borderColor: color }}>
      <p className="stat-label">{label}</p>
      <p className="stat-value" style={{ color }}>{value}</p>
      {sub && <p className="stat-sub">{sub}</p>}
    </div>
  );
}

function SectionHeader({ title }: { title: string }) {
  return <h2 className="analytics-section-header">{title}</h2>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Panel 1: Today Live
// ─────────────────────────────────────────────────────────────────────────────

function TodayPanel({ data }: { data: TodayData }) {
  const hourLabels = Array.from({ length: 24 }, (_, i) => {
    // Convert UTC hour to IST (+5:30)
    const istHour = (i + 5) % 24;
    return `${istHour.toString().padStart(2, "0")}:00`;
  });

  const hourlyChartData = data.orders_by_hour.map((count, i) => ({
    hour: hourLabels[i],
    orders: count,
  }));

  return (
    <div className="analytics-panel">
      <SectionHeader title={`Today — ${data.date}`} />

      <div className="stat-grid">
        <StatCard label="Orders"    value={data.orders_placed}    color={COLORS.cyan}  />
        <StatCard label="Revenue"   value={formatRupees(data.revenue_paise)} color={COLORS.amber} />
        <StatCard label="Collected" value={data.orders_collected} color={COLORS.green} />
        <StatCard label="Reprints"  value={data.reprints}
          color={data.reprints > 3 ? COLORS.red : COLORS.grey} />
        <StatCard label="Sessions"  value={data.sessions_started} color={COLORS.grey}  />
        <StatCard
          label="Avg Ready Time"
          value={formatMs(data.avg_order_to_ready_ms)}
          color={
            data.avg_order_to_ready_ms && data.avg_order_to_ready_ms > 840000
              ? COLORS.red : COLORS.cyan
          }
          sub="Target < 14 min"
        />
      </div>

      {/* Funnel */}
      <div className="funnel-row">
        {[
          { label: "Sessions",   value: data.funnel.sessions   },
          { label: "Stories",    value: data.funnel.stories    },
          { label: "Selections", value: data.funnel.selections },
          { label: "Orders",     value: data.funnel.orders     },
          { label: "Collected",  value: data.funnel.collected  },
        ].map((step, i, arr) => (
          <div key={step.label} className="funnel-step">
            <div className="funnel-value">{step.value}</div>
            <div className="funnel-label">{step.label}</div>
            {i < arr.length - 1 && (
              <div className="funnel-rate">
                {arr[i + 1].value > 0
                  ? `${((arr[i + 1].value / Math.max(step.value, 1)) * 100).toFixed(0)}%`
                  : "—"}
                →
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Hourly bar chart */}
      <p className="chart-label">Orders by Hour (IST)</p>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={hourlyChartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
          <XAxis dataKey="hour" tick={{ fontSize: 9, fill: "#888" }} interval={3} />
          <YAxis tick={{ fontSize: 9, fill: "#888" }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}
            labelStyle={{ color: "#fff" }}
          />
          <Bar dataKey="orders" fill={COLORS.cyan} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Panel 2: 14-Day Trend
// ─────────────────────────────────────────────────────────────────────────────

function TrendPanel({ summaries }: { summaries: DailySummary[] }) {
  const chartData = [...summaries].reverse().map(s => ({
    date:     s.date.slice(5), // MM-DD
    orders:   s.orders_placed,
    revenue:  Math.round(s.revenue_paise / 100),
    sessions: s.sessions_started,
    reprints: s.reprints,
    conv:     s.story_to_order_rate ? Math.round(s.story_to_order_rate * 100) : 0,
  }));

  const totalRevenue   = summaries.reduce((a, s) => a + s.revenue_paise, 0);
  const totalOrders    = summaries.reduce((a, s) => a + s.orders_placed, 0);
  const avgReadyMs     = summaries.filter(s => s.avg_order_to_ready_ms)
                           .map(s => s.avg_order_to_ready_ms!);
  const overallAvgReady = avgReadyMs.length
    ? avgReadyMs.reduce((a, b) => a + b, 0) / avgReadyMs.length
    : null;

  return (
    <div className="analytics-panel">
      <SectionHeader title="14-Day Trend" />

      <div className="stat-grid">
        <StatCard label="Total Revenue"   value={formatRupees(totalRevenue)} color={COLORS.amber} />
        <StatCard label="Total Orders"    value={totalOrders}                color={COLORS.cyan}  />
        <StatCard label="Avg Ready Time"  value={formatMs(overallAvgReady)}  color={COLORS.green} />
      </div>

      <p className="chart-label">Orders per Day</p>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#888" }} />
          <YAxis tick={{ fontSize: 9, fill: "#888" }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}
          />
          <Bar dataKey="orders" fill={COLORS.cyan} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      <p className="chart-label">Revenue per Day (₹)</p>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={chartData} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#888" }} />
          <YAxis tick={{ fontSize: 9, fill: "#888" }} />
          <Tooltip
            contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}
          />
          <Line type="monotone" dataKey="revenue" stroke={COLORS.amber}
                strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>

      <p className="chart-label">Story→Order Conversion % per Day</p>
      <ResponsiveContainer width="100%" height={100}>
        <LineChart data={chartData} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#888" }} />
          <YAxis tick={{ fontSize: 9, fill: "#888" }} domain={[0, 100]} />
          <Tooltip
            contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}
          />
          <Line type="monotone" dataKey="conv" stroke={COLORS.green}
                strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Panel 3: Product Intelligence
// ─────────────────────────────────────────────────────────────────────────────

function ProductPanel({ data }: { data: ProductData }) {
  const styleChartData = data.styles.slice(0, 8).map(s => ({
    style:   s.style,
    rate:    Math.round(s.selection_rate * 100),
    count:   s.selected,
  }));

  const colorChartData = data.colors.slice(0, 8).map(c => ({
    color: c.color,
    count: c.count,
  }));

  const reprints = Object.entries(data.reprint_analysis)
    .sort((a, b) => b[1].reprint_rate - a[1].reprint_rate);

  return (
    <div className="analytics-panel">
      <SectionHeader title="Product Intelligence" />

      {/* Style selection rates */}
      <p className="chart-label">Style Selection Rate (% of generated → purchased)</p>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={styleChartData} layout="vertical"
                  margin={{ top: 0, right: 20, left: 60, bottom: 0 }}>
          <XAxis type="number" tick={{ fontSize: 9, fill: "#888" }} domain={[0, 100]}
                 tickFormatter={v => `${v}%`} />
          <YAxis type="category" dataKey="style" tick={{ fontSize: 9, fill: "#ccc" }} width={55} />
          <Tooltip
            contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}
            formatter={(v: number) => [`${v}%`, "Selection rate"]}
          />
          <Bar dataKey="rate" radius={[0, 2, 2, 0]}>
            {styleChartData.map((_, i) => (
              <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Colour distribution */}
      <p className="chart-label">Orders by Colour</p>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={colorChartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
          <XAxis dataKey="color" tick={{ fontSize: 9, fill: "#888" }} />
          <YAxis tick={{ fontSize: 9, fill: "#888" }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}
          />
          <Bar dataKey="count" fill={COLORS.amber} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* Reprint analysis */}
      <p className="chart-label">Reprint Rate by Colour</p>
      <table className="analytics-table">
        <thead>
          <tr>
            <th>Colour</th><th>Orders</th><th>Reprints</th><th>Rate</th>
          </tr>
        </thead>
        <tbody>
          {reprints.map(([color, data]) => (
            <tr key={color}>
              <td>{color}</td>
              <td>{data.orders}</td>
              <td>{data.reprints}</td>
              <td style={{ color: data.reprint_rate > 0.1 ? COLORS.red : COLORS.green }}>
                {(data.reprint_rate * 100).toFixed(1)}%
              </td>
            </tr>
          ))}
          {reprints.length === 0 && (
            <tr><td colSpan={4} style={{ color: COLORS.grey }}>No reprint data yet</td></tr>
          )}
        </tbody>
      </table>

      {/* Top products */}
      <p className="chart-label">Top Product + Size Combinations</p>
      <table className="analytics-table">
        <thead><tr><th>Product</th><th>Orders</th></tr></thead>
        <tbody>
          {data.products.slice(0, 8).map(p => (
            <tr key={p.product_size}>
              <td>{p.product_size}</td>
              <td>{p.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Panel 4: Operational
// ─────────────────────────────────────────────────────────────────────────────

function OperationalPanel({
  summaries, funnel,
}: { summaries: DailySummary[]; funnel: FunnelData }) {
  const latencyData = [...summaries].reverse()
    .filter(s => s.avg_order_to_ready_ms)
    .map(s => ({
      date:    s.date.slice(5),
      avg:     Math.round((s.avg_order_to_ready_ms || 0) / 1000 / 60 * 10) / 10,
      p95:     Math.round((s.p95_order_to_ready_ms || 0) / 1000 / 60 * 10) / 10,
    }));

  return (
    <div className="analytics-panel">
      <SectionHeader title="Operational" />

      {/* Funnel totals */}
      <div className="stat-grid">
        <StatCard
          label="Session→Order"
          value={formatPct(funnel.conversion_rates.session_to_order)}
          color={COLORS.cyan}
        />
        <StatCard
          label="Story→Order"
          value={formatPct(funnel.conversion_rates.story_to_order)}
          color={COLORS.amber}
        />
        <StatCard
          label="Order→Collected"
          value={formatPct(funnel.conversion_rates.order_to_collected)}
          color={COLORS.green}
        />
      </div>

      {/* Order-to-ready latency trend */}
      <p className="chart-label">Order→Ready Time (minutes, 14-day avg + p95)</p>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={latencyData} margin={{ top: 0, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#888" }} />
          <YAxis tick={{ fontSize: 9, fill: "#888" }} />
          {/* 14-minute journey promise reference line */}
          <Tooltip
            contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}
            formatter={(v: number) => [`${v} min`]}
          />
          <Legend wrapperStyle={{ fontSize: 9, color: "#888" }} />
          <Line type="monotone" dataKey="avg" stroke={COLORS.cyan}
                strokeWidth={2} dot={false} name="Avg" />
          <Line type="monotone" dataKey="p95" stroke={COLORS.red}
                strokeWidth={1} dot={false} strokeDasharray="4 2" name="p95" />
        </LineChart>
      </ResponsiveContainer>

      {/* Reprint + failure counts */}
      <p className="chart-label">Reprints + Failed Variants per Day</p>
      <ResponsiveContainer width="100%" height={100}>
        <BarChart
          data={[...summaries].reverse().map(s => ({
            date:     s.date.slice(5),
            reprints: s.reprints,
            failed:   s.variants_failed,
          }))}
          margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#888" }} />
          <YAxis tick={{ fontSize: 9, fill: "#888" }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}` }}
          />
          <Legend wrapperStyle={{ fontSize: 9, color: "#888" }} />
          <Bar dataKey="reprints" fill={COLORS.red}   radius={[2, 2, 0, 0]} name="Reprints"       stackId="a" />
          <Bar dataKey="failed"   fill={COLORS.amber} radius={[2, 2, 0, 0]} name="Failed variants" stackId="a" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main dashboard
// ─────────────────────────────────────────────────────────────────────────────

export function AnalyticsDashboard() {
  const [today,     setToday]     = useState<TodayData | null>(null);
  const [summaries, setSummaries] = useState<DailySummary[]>([]);
  const [product,   setProduct]   = useState<ProductData | null>(null);
  const [funnel,    setFunnel]    = useState<FunnelData | null>(null);
  const [loading,   setLoading]   = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [todayRes, dailyRes, productRes, funnelRes] = await Promise.all([
        fetch("/api/v1/analytics/today"),
        fetch("/api/v1/analytics/daily?days=14"),
        fetch("/api/v1/analytics/product?days=14"),
        fetch("/api/v1/analytics/funnel?days=14"),
      ]);
      const [todayData, dailyData, productData, funnelData] = await Promise.all([
        todayRes.json(), dailyRes.json(), productRes.json(), funnelRes.json(),
      ]);
      setToday(todayData);
      setSummaries(dailyData.summaries || []);
      setProduct(productData);
      setFunnel(funnelData);
      setLastRefresh(new Date());
    } catch (err) {
      console.error("Analytics fetch failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchAll, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  return (
    <div className="analytics-dashboard">
      <header className="analytics-header">
        <h1>BOBB Analytics</h1>
        <div className="analytics-header-right">
          {lastRefresh && (
            <span className="analytics-refresh-time">
              Updated {lastRefresh.toLocaleTimeString("en-IN", {
                hour: "2-digit", minute: "2-digit",
              })}
            </span>
          )}
          <button className="btn btn--secondary" onClick={fetchAll} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </header>

      {loading && !today ? (
        <div className="analytics-loading">Loading analytics…</div>
      ) : (
        <div className="analytics-grid">
          {today    && <TodayPanel       data={today}                      />}
          {summaries.length > 0 && <TrendPanel summaries={summaries}      />}
          {product  && <ProductPanel     data={product}                    />}
          {summaries.length > 0 && funnel && (
            <OperationalPanel summaries={summaries} funnel={funnel} />
          )}
        </div>
      )}
    </div>
  );
}
