from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx


ROOT = Path(__file__).resolve().parent
REQUIRED_HANDOFFS = (
    ("developer", "api"),
    ("api", "orchestrator"),
    ("orchestrator", "repo_adapter"),
    ("repo_adapter", "repository"),
    ("orchestrator", "llm"),
    ("orchestrator", "validator"),
    ("orchestrator", "runner"),
    ("repository", "runner"),
    ("orchestrator", "git_host"),
    ("git_host", "reviewer"),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def graph_from_adjacency(adjacency: dict[str, dict[str, int]]) -> nx.DiGraph:
    graph = nx.DiGraph()
    node_ids = list(adjacency)
    graph.add_nodes_from(node_ids)
    for source in node_ids:
        for target in node_ids:
            if adjacency[source][target]:
                graph.add_edge(source, target)
    return graph


def remove_vertex_from_matrix(
    adjacency: dict[str, dict[str, int]],
    removed: str,
) -> dict[str, dict[str, int]]:
    remaining = [node for node in adjacency if node != removed]
    return {
        source: {target: adjacency[source][target] for target in remaining}
        for source in remaining
    }


def write_matrix(path: Path, adjacency: dict[str, dict[str, int]]) -> None:
    node_ids = list(adjacency)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["id", *node_ids])
        for source in node_ids:
            writer.writerow(
                [source, *(adjacency[source][target] for target in node_ids)]
            )


def load_graph() -> tuple[
    nx.DiGraph,
    dict[str, str],
    dict[tuple[str, str], str],
    dict[str, dict[str, int]],
]:
    nodes = read_csv(ROOT / "nodes.csv")
    matrix_path = ROOT / "adjacency.csv"
    with matrix_path.open(encoding="utf-8", newline="") as file:
        matrix_reader = csv.reader(file)
        header = next(matrix_reader)
        node_ids = header[1:]
        rows = list(matrix_reader)

    labels = {row["id"]: row["label"] for row in nodes}
    if set(node_ids) != set(labels) or len(node_ids) != len(labels):
        raise ValueError("nodes.csv and adjacency.csv must contain the same unique node IDs")
    if [row[0] for row in rows] != node_ids:
        raise ValueError("Adjacency matrix row order must match its column order")

    adjacency: dict[str, dict[str, int]] = {}
    for row in rows:
        source, *values = row
        if len(values) != len(node_ids):
            raise ValueError(f"Invalid matrix row for {source}: expected {len(node_ids)} values")
        for target, value in zip(node_ids, values, strict=True):
            if value not in {"0", "1"}:
                raise ValueError(f"Adjacency values must be 0 or 1, got {value!r}")
        adjacency[source] = {
            target: int(value) for target, value in zip(node_ids, values, strict=True)
        }

    graph = graph_from_adjacency(adjacency)

    edge_rows = read_csv(ROOT / "edges.csv")
    edge_types: dict[tuple[str, str], str] = {}
    for edge in edge_rows:
        pair = (edge["source"], edge["target"])
        if pair in edge_types:
            raise ValueError(f"Duplicate typed edge: {pair}")
        if pair[0] not in graph or pair[1] not in graph:
            raise ValueError(f"Edge refers to an unknown node: {pair}")
        edge_types[pair] = edge["type"]

    if set(graph.edges) != set(edge_types):
        raise ValueError("edges.csv and adjacency.csv describe different edges")
    return graph, labels, edge_types, adjacency


def is_mission_workable(graph: nx.DiGraph) -> bool:
    if not all(node in graph for handoff in REQUIRED_HANDOFFS for node in handoff):
        return False
    return all(nx.has_path(graph, source, target) for source, target in REQUIRED_HANDOFFS)


def create_graph_image(
    graph: nx.DiGraph,
    labels: dict[str, str],
    edge_types: dict[tuple[str, str], str],
) -> None:
    pos = nx.spring_layout(graph, seed=21, k=1.4, iterations=250)
    fig, axis = plt.subplots(figsize=(15, 10))
    colors = {
        "human": "#f4c95d",
        "service": "#69b3a2",
        "system": "#6c8ebf",
        "external": "#b39ddb",
    }
    node_kinds = {row["id"]: row["kind"] for row in read_csv(ROOT / "nodes.csv")}
    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=[colors[node_kinds[node]] for node in graph.nodes],
        node_size=2800,
        edgecolors="#243447",
        linewidths=1.2,
        ax=axis,
    )
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=9, ax=axis)

    edge_colors = {"data": "#3973ac", "commands": "#bd5b31"}
    for source, target in graph.edges:
        reverse_exists = graph.has_edge(target, source)
        if reverse_exists:
            radius = 0.18 if source < target else -0.18
        else:
            radius = 0.02
        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=[(source, target)],
            edge_color=edge_colors[edge_types[(source, target)]],
            width=1.7,
            arrows=True,
            arrowsize=18,
            connectionstyle=f"arc3,rad={radius}",
            min_source_margin=22,
            min_target_margin=22,
            ax=axis,
        )
    nx.draw_networkx_edge_labels(
        graph,
        pos,
        edge_labels={
            edge: "данные" if kind == "data" else "команды"
            for edge, kind in edge_types.items()
        },
        font_size=7,
        label_pos=0.5,
        rotate=False,
        bbox={"alpha": 0.75, "color": "white", "pad": 1},
        ax=axis,
    )
    axis.set_title("Целевая архитектура Test Writer — направленный граф")
    axis.axis("off")
    fig.tight_layout()
    svg_path = ROOT / "graph.svg"
    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    svg_path.write_text(
        "\n".join(
            line.rstrip()
            for line in svg_path.read_text(encoding="utf-8").splitlines()
        )
        + "\n",
        encoding="utf-8",
    )


def create_report(
    graph: nx.DiGraph,
    labels: dict[str, str],
    adjacency: dict[str, dict[str, int]],
) -> str:
    weak_components = nx.number_weakly_connected_components(graph)
    strong_components = nx.number_strongly_connected_components(graph)
    shortest_path = nx.shortest_path(graph, "developer", "reviewer")
    betweenness = nx.betweenness_centrality(graph, normalized=True)

    removal_rows: list[tuple[str, int, bool]] = []
    for node in graph.nodes:
        reduced_adjacency = remove_vertex_from_matrix(adjacency, node)
        reduced = graph_from_adjacency(reduced_adjacency)
        components = nx.number_weakly_connected_components(reduced)
        removal_rows.append((node, components, is_mission_workable(reduced)))

    primary = max(
        removal_rows,
        key=lambda row: (
            row[1],
            graph.in_degree(row[0]) + graph.out_degree(row[0]),
            betweenness[row[0]],
        ),
    )
    cut_vertices = sorted(nx.articulation_points(graph.to_undirected()))
    selected_removal = graph_from_adjacency(
        remove_vertex_from_matrix(adjacency, primary[0])
    )
    component_details = " | ".join(
        ", ".join(sorted(component))
        for component in sorted(
            nx.weakly_connected_components(selected_removal),
            key=lambda component: sorted(component),
        )
    )

    lines = [
        "Граф целевой архитектуры Test Writer",
        f"Вершины: {graph.number_of_nodes()}",
        f"Направленные рёбра: {graph.number_of_edges()}",
        f"Слабые компоненты до удаления: {weak_components}",
        f"Сильные компоненты до удаления: {strong_components}",
        "Кратчайший путь developer -> reviewer: "
        + " -> ".join(shortest_path)
        + f" ({len(shortest_path) - 1} рёбер)",
        "",
        "Степени и нормированная betweenness centrality:",
        "node,in_degree,out_degree,total_degree,betweenness",
    ]
    for node in graph.nodes:
        in_degree = graph.in_degree(node)
        out_degree = graph.out_degree(node)
        lines.append(
            f"{node},{in_degree},{out_degree},{in_degree + out_degree},"
            f"{betweenness[node]:.4f}"
        )

    lines.extend(
        [
            "",
            "Удаление вершин:",
            "node,weak_components_after_removal,mission_handoffs_available",
        ]
    )
    for node, component_count, mission_available in removal_rows:
        lines.append(f"{node},{component_count},{str(mission_available).lower()}")

    lines.extend(
        [
            "",
            "Структурные точки сочленения (неориентированный вид графа): "
            + (", ".join(cut_vertices) if cut_vertices else "нет"),
            f"Максимальная фрагментация при одиночном удалении: {primary[0]} "
            f"({primary[1]} слабые компоненты)",
            "Компоненты после удаления этой вершины: " + component_details,
            "Названия вершин: "
            + "; ".join(f"{node}={labels[node]}" for node in graph.nodes),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    graph, labels, edge_types, adjacency = load_graph()
    if not nx.has_path(graph, "developer", "reviewer"):
        raise ValueError("The baseline graph must connect developer to reviewer")
    write_matrix(
        ROOT / "adjacency_without_orchestrator.csv",
        remove_vertex_from_matrix(adjacency, "orchestrator"),
    )
    create_graph_image(graph, labels, edge_types)
    report = create_report(graph, labels, adjacency)
    (ROOT / "results.txt").write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
