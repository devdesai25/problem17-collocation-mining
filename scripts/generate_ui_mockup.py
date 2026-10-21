"""Generate a realistic web application UI mockup graphic for presentation slides."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from pathlib import Path

CHARTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(12, 6.8), dpi=200)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")

# Background Window
window = FancyBboxPatch((2, 2), 96, 96, boxstyle="round,pad=0.5,rounding_size=1.5",
                        facecolor="#F8FAFC", edgecolor="#CBD5E1", linewidth=1.5)
ax.add_patch(window)

# Browser header bar
header = FancyBboxPatch((2, 92), 96, 6, boxstyle="round,pad=0,rounding_size=1.5",
                         facecolor="#1E293B", edgecolor="none")
ax.add_patch(header)
# Window dots
ax.plot([5, 7, 9], [95, 95, 95], "o", markersize=6, color="#94A3B8")
ax.text(50, 95, "http://localhost:8501 — Collocation Mining & Association Scoring Engine",
        ha="center", va="center", color="#E2E8F0", fontsize=9, fontfamily="sans-serif")

# Sidebar
sidebar = Rectangle((2, 2), 24, 90, facecolor="#0F172A", edgecolor="#334155", linewidth=1)
ax.add_patch(sidebar)
ax.text(14, 88, "⚙️ Controls", ha="center", va="center", color="#F8FAFC", fontsize=11, fontweight="bold")
ax.text(4, 82, "Data Source:", color="#94A3B8", fontsize=8, fontweight="bold")
ax.text(5, 78, "● MeetingBank Corpus", color="#38BDF8", fontsize=8)
ax.text(5, 74, "○ Custom Dictation", color="#64748B", fontsize=8)

ax.text(4, 67, "N-Gram Order:", color="#94A3B8", fontsize=8, fontweight="bold")
ax.text(5, 63, "▶ Bigram (2-word)", color="#F8FAFC", fontsize=8)

ax.text(4, 56, "Min Frequency: f ≥ 3", color="#94A3B8", fontsize=8, fontweight="bold")
ax.text(4, 49, "Primary Metric:", color="#94A3B8", fontsize=8, fontweight="bold")
ax.text(5, 45, "PMI (Pointwise Mutual Inf)", color="#38BDF8", fontsize=8)

ax.text(4, 38, "Stopword Policy:", color="#94A3B8", fontsize=8, fontweight="bold")
ax.text(5, 34, "☑ Keep Stopwords (Main)", color="#10B981", fontsize=8)

# Main Title Area
ax.text(29, 86, "🎙️ Collocation Mining & Association Scoring Engine",
        color="#0F172A", fontsize=14, fontweight="bold")
ax.text(29, 82, "Executive Voice Memo Analysis | Problem 17 (MT-AIML Sem 5)",
        color="#64748B", fontsize=9)

# KPI Cards
kpis = [
    ("Sentences", "1,772", "#2563EB"),
    ("Tokens", "67,046", "#0D9488"),
    ("Unique Bigrams", "18,485", "#7C3AED"),
    ("Gold Target Hit", "95% Prec@20", "#16A34A"),
]
for i, (title, val, color) in enumerate(kpis):
    x = 29 + i * 17
    card = FancyBboxPatch((x, 70), 15.5, 9, boxstyle="round,pad=0.2,rounding_size=0.8",
                          facecolor="white", edgecolor="#E2E8F0", linewidth=1)
    ax.add_patch(card)
    ax.text(x + 7.75, 76.5, title, ha="center", va="center", color="#64748B", fontsize=7.5)
    ax.text(x + 7.75, 73, val, ha="center", va="center", color=color, fontsize=10.5, fontweight="bold")

# Tabs
ax.plot([29, 96], [66, 66], color="#E2E8F0", linewidth=1.5)
ax.plot([29, 52], [66, 66], color="#2563EB", linewidth=2.5)
ax.text(40.5, 67.5, "📊 Top-20 Extracted Collocations", ha="center", va="center", color="#2563EB", fontsize=8.5, fontweight="bold")
ax.text(65, 67.5, "⚖️ Multi-Metric Comparison", ha="center", va="center", color="#64748B", fontsize=8.5)
ax.text(85, 67.5, "🔬 2×2 Contingency Inspector", ha="center", va="center", color="#64748B", fontsize=8.5)

# Table Box
t_box = FancyBboxPatch((29, 6), 67, 57, boxstyle="round,pad=0.2,rounding_size=0.8",
                       facecolor="white", edgecolor="#E2E8F0", linewidth=1)
ax.add_patch(t_box)

# Table Headers
headers = ["Rank", "Collocation Phrase", "Score", "Joint Freq", "Left Marg (w1)", "Right Marg (w2)", "Category"]
col_x = [31, 36, 54, 63, 72, 82, 91]
for h, cx in zip(headers, col_x):
    ax.text(cx, 60, h, color="#475569", fontsize=7.5, fontweight="bold")
ax.plot([30, 95], [58, 58], color="#CBD5E1", linewidth=0.8)

# Table Rows
sample_rows = [
    ("#1", "boot camp", "14.59", "4", "4", "4", "genuine"),
    ("#2", "coffee shop", "14.59", "3", "3", "3", "genuine"),
    ("#3", "dry ice", "14.42", "8", "8", "9", "genuine"),
    ("#4", "council member", "9.73", "69", "70", "72", "genuine"),
    ("#5", "domestic violence", "14.18", "6", "6", "8", "genuine"),
    ("#6", "real estate", "13.85", "11", "12", "14", "genuine"),
    ("#7", "solid waste", "13.62", "9", "10", "11", "genuine"),
    ("#8", "long beach", "13.51", "12", "13", "15", "genuine"),
    ("#9", "task force", "13.20", "15", "17", "18", "genuine"),
    ("#10", "annual action plan", "12.98", "4", "4", "5", "acceptable"),
]

for idx, row in enumerate(sample_rows):
    y = 54.5 - idx * 4.8
    bg_color = "#F8FAFC" if idx % 2 == 1 else "white"
    row_bg = Rectangle((30, y - 2), 65, 4.2, facecolor=bg_color, edgecolor="none")
    ax.add_patch(row_bg)
    for val, cx in zip(row, col_x):
        c_color = "#0F172A"
        fw = "normal"
        if cx == 36:
            fw = "bold"
        elif cx == 91:
            c_color = "#16A34A" if val == "genuine" else "#D97706"
            fw = "bold"
        ax.text(cx, y, val, color=c_color, fontsize=7.5, fontweight=fw)

plt.tight_layout()
out_path = CHARTS_DIR / "web_app_ui.png"
fig.savefig(out_path, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"Generated web UI mockup at {out_path}")
