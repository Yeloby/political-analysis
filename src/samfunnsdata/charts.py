from pathlib import Path

import matplotlib.pyplot as plt

from .analysis import observation_value


def population_figure(series, title: str):
    fig, ax = plt.subplots(figsize=(12, 6))

    for label, frame in series:
        years = frame["Tid_code"].astype(int)
        values = [observation_value(row) for _, row in frame.iterrows()]

        ax.plot(
            years,
            values,
            marker="o",
            markersize=3,
            label=label,
        )

    ax.set_title(title)
    ax.set_xlabel("År")
    ax.set_ylabel("Innbyggere")
    ax.grid(True, alpha=0.25)

    if len(series) > 1:
        ax.legend()

    fig.tight_layout()
    return fig


def population_chart(
    series,
    output: str | Path,
    title: str,
):
    output = Path(output)

    fig = population_figure(series, title)
    fig.savefig(output, dpi=160)
    plt.close(fig)

    return output


def election_figure(frame, title: str):
    fig, ax = plt.subplots(figsize=(12, 6))

    years = frame["year"].astype(int)
    values = [observation_value(row, "percent") for _, row in frame.iterrows()]

    ax.plot(
        years,
        values,
        marker="o",
        markersize=4,
    )

    ax.set_title(title)
    ax.set_xlabel("Valgår")
    ax.set_ylabel("Stemmer (%)")
    ax.grid(True, alpha=0.25)

    fig.tight_layout()
    return fig
