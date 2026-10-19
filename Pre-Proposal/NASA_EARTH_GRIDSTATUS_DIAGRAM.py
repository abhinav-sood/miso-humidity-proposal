import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(13, 8))
ax.set_xlim(0, 13)
ax.set_ylim(0, 8)
ax.axis("off")

BLUE, GREEN, GRAY, GOLD = "#2F6DB5", "#2E8B57", "#4A4A4A", "#C98A10"


def box(x, y, w, h, title, lines, color, title_size=13):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15",
                                fc=color + "22", ec=color, lw=2))
    ax.text(x + w / 2, y + h - 0.35, title, ha="center", va="center",
            fontsize=title_size, fontweight="bold", color=color)
    for i, line in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.85 - i * 0.38, line, ha="center",
                va="center", fontsize=12, color="#222")


def arrow(p1, p2, color=GRAY, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=18,
                                 color=color, lw=2, linestyle=ls))


# Top row
box(0.4, 4.6, 3.6, 2.6, "NASA Earth Data / NASA POWER",
    ["Solar irradiance", "Temperature & humidity", "Wind & precipitation",
     "Satellite / reanalysis (MERRA-2)"], BLUE)
box(9.0, 4.6, 3.6, 2.6, "Grid Status",
    ["Real-time & historical load", "Generation mix & prices (LMPs)",
     "Interconnection queues", "ISO/RTO market data"], GREEN)

# Center integration layer
box(4.9, 4.6, 3.2, 2.6, "Integration Layer",
    ["Common APIs (REST / JSON)", "Time & location alignment",
     "Unit / schema harmonization", "Unified datasets"], GOLD)

arrow((4.0, 5.9), (4.9, 5.9), BLUE)
arrow((9.0, 5.9), (8.1, 5.9), GREEN)

# Downstream users
users = ["Grid\noperators", "Utilities", "Transmission\nplanners", "Investors",
         "Legal /\nregulatory users", "Researchers"]
n = len(users)
w, gap = 1.8, 0.2
total = n * w + (n - 1) * gap
x0 = (13 - total) / 2
ax.text(6.5, 0.35, "Downstream users and applications", ha="center",
        fontsize=13, fontweight="bold", color=GRAY)

BUS_Y = 3.5
centers = [x0 + i * (w + gap) + w / 2 for i in range(n)]
# trunk from integration layer down to the bus, then the bus across
ax.plot([6.5, 6.5], [4.55, BUS_Y], color=GRAY, lw=2, solid_capstyle="round")
ax.plot([centers[0], centers[-1]], [BUS_Y, BUS_Y], color=GRAY, lw=2, solid_capstyle="round")

for i, u in enumerate(users):
    x = x0 + i * (w + gap)
    ax.add_patch(FancyBboxPatch((x, 0.8), w, 1.5, boxstyle="round,pad=0.04,rounding_size=0.12",
                                fc="#EEEEEE", ec=GRAY, lw=1.6))
    ax.text(x + w / 2, 1.55, u, ha="center", va="center", fontsize=11, color="#222")
    arrow((centers[i], BUS_Y), (centers[i], 2.4), GRAY)

ax.text(6.5, 7.75, "Figure 2. Integrating NASA Earth data with electricity-system data",
        ha="center", fontsize=15, fontweight="bold")

plt.tight_layout()
plt.savefig("miso-humidity-proposalfigure2.png", dpi=200, bbox_inches="tight", facecolor="white")
plt.savefig("miso-humidity-proposalfigure2.pdf", bbox_inches="tight", facecolor="white")
print("saved")