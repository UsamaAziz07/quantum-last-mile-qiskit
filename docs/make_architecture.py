"""OWNER: USAMA — only USAMA edits this file.
Draws the hybrid Quantum-Classical Last-Mile delivery pipeline architecture.
Outputs: docs/architecture.png (200 dpi).
Pure matplotlib, deterministic, offline.
"""
from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


def draw_architecture(output_path: Path) -> None:
    # Set up figure
    fig, ax = plt.subplots(figsize=(16, 8.5), dpi=200)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8.5)
    ax.axis("off")

    # Color palette
    c_blue_bg = "#E0F2FE"       # Light blue
    c_blue_border = "#0284C7"   # Dark blue
    c_purple_bg = "#F3E8FF"     # Light purple
    c_purple_border = "#7E22CE" # Dark purple
    c_amber_bg = "#FEF3C7"      # Light amber
    c_amber_border = "#D97706"  # Dark amber
    c_green_bg = "#DCFCE7"      # Light green
    c_green_border = "#16A34A"  # Dark green
    c_arrow = "#475569"

    def draw_box(x, y, w, h, title, subtitle, bg, border, fontsize_title=10.5, fontsize_sub=8.5):
        # Draw fancy rounded rectangle
        box = FancyBboxPatch(
            (x - w / 2, y - h / 2),
            w,
            h,
            boxstyle="round,pad=0.15,rounding_size=0.15",
            facecolor=bg,
            edgecolor=border,
            linewidth=1.8,
            zorder=3,
        )
        ax.add_patch(box)
        # Add text
        if subtitle:
            ax.text(
                x,
                y + 0.16,
                title,
                ha="center",
                va="center",
                fontsize=fontsize_title,
                fontweight="bold",
                color="#0F172A",
                zorder=4,
            )
            ax.text(
                x,
                y - 0.22,
                subtitle,
                ha="center",
                va="center",
                fontsize=fontsize_sub,
                color="#334155",
                style="italic",
                zorder=4,
            )
        else:
            ax.text(
                x,
                y,
                title,
                ha="center",
                va="center",
                fontsize=fontsize_title,
                fontweight="bold",
                color="#0F172A",
                zorder=4,
            )

    def draw_arrow(x1, y1, x2, y2, label=None, rad=0.0, linestyle="solid", color=c_arrow):
        arrow = FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>,head_length=5,head_width=3.5",
            color=color,
            linewidth=1.6,
            linestyle=linestyle,
            zorder=2,
        )
        ax.add_patch(arrow)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(
                mx,
                my + 0.18,
                label,
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
                color="#475569",
                bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.8),
                zorder=5,
            )

    # ----------------- Title & Legend -----------------
    ax.text(
        8.0,
        8.0,
        "Hybrid Quantum-Classical Architecture: Last-Mile Delivery (QAOA)",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="#0F172A",
    )
    ax.text(
        8.0,
        7.6,
        "Cluster-First (Quantum Assignment) · Route-Second (Exact Classical TSP) · Multi-Vehicle Balancing",
        ha="center",
        va="center",
        fontsize=10.5,
        color="#475569",
    )

    # Legend at bottom
    leg_y = 0.55
    legend_items = [
        ("Classical Components", c_blue_bg, c_blue_border),
        ("Quantum Algorithms & Hamiltonians", c_purple_bg, c_purple_border),
        ("Classical Optimization Loop", c_amber_bg, c_amber_border),
        ("Evaluation & Integration", c_green_bg, c_green_border),
    ]
    start_lx = 2.2
    for idx, (lbl, bg, bd) in enumerate(legend_items):
        lx = start_lx + idx * 3.2
        patch = FancyBboxPatch(
            (lx - 0.25, leg_y - 0.12),
            0.5,
            0.24,
            boxstyle="round,pad=0.04,rounding_size=0.06",
            facecolor=bg,
            edgecolor=bd,
            linewidth=1.5,
        )
        ax.add_patch(patch)
        ax.text(lx + 0.38, leg_y, lbl, ha="left", va="center", fontsize=8.5, fontweight="medium", color="#1E293B")

    # ----------------- Blocks Placement -----------------
    # 1. Instance Input (Shared input node)
    draw_box(1.5, 4.6, 2.2, 1.2, "Instance JSON", "Coordinates, Demands,\nVan Capacity Q=7", c_blue_bg, c_blue_border)

    # Upper track: Quantum Pipeline
    y_q = 5.9
    w_std = 1.9
    h_std = 1.05

    draw_box(4.0, y_q, w_std, h_std, "Model Builder", "QuadraticProgram\nVariables & Constraints", c_blue_bg, c_blue_border)
    draw_box(6.3, y_q, w_std, h_std, "QUBO Converter", "Slack Variables +\nPenalty Embedding", c_purple_bg, c_purple_border)
    draw_box(8.6, y_q, w_std, h_std, "Ising Hamiltonian", "Cost Operator H_C\n12 Qubits Total", c_purple_bg, c_purple_border)
    draw_box(11.0, y_q, 2.1, h_std, "QAOA Circuit", "p layers (γ, β)\nQiskit Aer Simulator", c_purple_bg, c_purple_border)

    # Optimizer Loop below QAOA
    draw_box(11.0, 4.3, 2.1, 0.95, "COBYLA Optimizer", "Classical Angle Tuning\nIterative Minimization", c_amber_bg, c_amber_border)

    # Downstream Quantum Pipeline (Right side coming down)
    draw_box(14.0, y_q, 1.9, h_std, "Bitstring Sampling", "Measurement Counts\nEigenstate Probabilities", c_purple_bg, c_purple_border)
    draw_box(14.0, 4.3, 1.9, 0.95, "Decode & Filter", "Strip Slack Qubits\nFeasibility Check", c_blue_bg, c_blue_border)
    draw_box(14.0, 2.6, 1.9, 0.95, "Exact TSP Routing", "Permutation Search\nper Assigned Van", c_blue_bg, c_blue_border)

    # Lower track: Classical Baselines
    y_c = 2.6
    draw_box(4.5, y_c, 2.8, 1.1, "Classical Baselines", "1. Exact Brute Force (64)\n2. Angular Greedy Sweep\n3. Simulated Annealing", c_blue_bg, c_blue_border)

    # Merge block: Evaluation & Pareto Analysis
    draw_box(9.2, y_c, 2.8, 1.1, "Evaluation & Metrics", "Model Objective vs True Route\nPareto Front (Beta Sweep)\nRuntime & Approximation Gap", c_green_bg, c_green_border)

    # ----------------- Connections / Arrows -----------------
    # Input to Model Builder (Quantum track)
    draw_arrow(2.6, 4.9, 3.05, 5.7, rad=-0.1)

    # Input to Classical Baselines (Classical track)
    draw_arrow(2.6, 4.3, 3.1, 2.8, rad=0.1)

    # Quantum Pipeline sequence
    draw_arrow(4.95, y_q, 5.35, y_q)
    draw_arrow(7.25, y_q, 7.65, y_q)
    draw_arrow(9.55, y_q, 9.95, y_q)
    draw_arrow(12.05, y_q, 13.05, y_q)

    # QAOA <--> COBYLA loop
    # Down arrow from QAOA to COBYLA
    draw_arrow(10.7, y_q - 0.525, 10.7, 4.775, rad=0.15, label="Expectation ⟨H_C⟩", color=c_amber_border)
    # Up arrow from COBYLA to QAOA
    draw_arrow(11.3, 4.775, 11.3, y_q - 0.525, rad=0.15, label="Updated (γ, β)", color=c_amber_border)

    # Downstream from Sampling -> Decode -> TSP
    draw_arrow(14.0, y_q - 0.525, 14.0, 4.775)
    draw_arrow(14.0, 3.825, 14.0, 3.075)

    # TSP to Evaluation
    draw_arrow(13.05, y_c, 10.6, y_c, label="Quantum Solution")

    # Classical Baselines to Evaluation
    draw_arrow(5.9, y_c, 7.8, y_c, label="Ground Truths")

    # Output to disk annotations
    ax.text(
        9.2,
        1.55,
        "Outputs: results/results.csv · summary.json · route_map.png · pareto.png",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="semibold",
        color="#334155",
        bbox=dict(boxstyle="round,pad=0.25", fc="#F8FAFC", ec="#CBD5E1", lw=1),
    )

    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Architecture diagram successfully saved to {output_path}")


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent
    out = root_dir / "docs" / "architecture.png"
    draw_architecture(out)
