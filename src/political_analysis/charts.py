from pathlib import Path

import matplotlib.pyplot as plt


def population_chart(
    series,
    output: str | Path,
    title: str,
):
    output = Path(output)

    fig, ax = plt.subplots(figsize=(10, 6))

    for label, frame in series:
        years = frame["Tid_code"].astype(int)
        values = frame["value"].astype(float)

        ax.plot(years, values, marker="o", markersize=3, label=label)

    ax.set_title(title)
    ax.set_xlabel("År")
    ax.set_ylabel("Innbyggere")
    ax.grid(True, alpha=0.25)

    if len(series) > 1:
        ax.legend()

    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)

    return output
