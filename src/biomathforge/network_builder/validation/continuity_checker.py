import pandas as pd
import networkx as nx
from typing import Tuple, List, Optional

from biomathforge.shared.utils.logger import BioMathForgeLogger

def check_network_continuity(
    network_dataframe: pd.DataFrame,
    logger: Optional[BioMathForgeLogger] = None
) -> Tuple[bool, List[str], List[str]]:
    """
    Check whether the network is weakly connected and return source and sink nodes.

    Args:
        network_dataframe (pd.DataFrame): Network edges with 'from' and 'to' columns.
        logger (Optional[BioMathForgeLogger]): Logger instance for consistent logging.

    Returns:
        Tuple of (is_connected, source_nodes, sink_nodes)
    """
    logger = logger or BioMathForgeLogger("network_validator")

    G = nx.from_pandas_edgelist(network_dataframe, 'from', 'to', create_using=nx.DiGraph())

    # Remove orphan dummy nodes
    dummy_nodes = [
        node for node in G.nodes()
        if isinstance(node, str) and node.startswith('r') and node[1:].isdigit()
        and (G.in_degree(node) == 0 or G.out_degree(node) == 0)
    ]
    G.remove_nodes_from(dummy_nodes)

    # Check continuity
    components = list(nx.weakly_connected_components(G))
    is_connected = len(components) == 1

    if not is_connected:
        subgraph_sources = []
        subgraph_sinks = []
        for i, component in enumerate(components, start=1):
            subG = G.subgraph(component)

            # Identify source nodes (no in-edges)
            min_in = min(dict(subG.in_degree()).values())
            source_nodes = [
                node for node, deg in subG.in_degree()
                if deg == min_in and not (isinstance(node, str) and node.startswith('r') and node[1:].isdigit())
            ]
            subgraph_sources.append(source_nodes)

            # Identify sink nodes (no out-edges)
            min_out = min(dict(subG.out_degree()).values())
            sink_nodes = [
                node for node, deg in subG.out_degree()
                if deg == min_out and not (isinstance(node, str) and node.startswith('r') and node[1:].isdigit())
            ]
            subgraph_sinks.append(sink_nodes)

            logger.warning(f"Subnetwork {i} detected:\nSources: {source_nodes} \nSinks: {sink_nodes}")
        return False, subgraph_sources, subgraph_sinks
    else:
        logger.info("✅ Network is weakly connected")

        # Return union of source/sink nodes for the entire graph
        source_nodes = [
            node for node in G.nodes()
            if G.in_degree(node) == 0 and not (isinstance(node, str) and node.startswith('r') and node[1:].isdigit())
        ]
        sink_nodes = [
            node for node in G.nodes()
            if G.out_degree(node) == 0 and not (isinstance(node, str) and node.startswith('r') and node[1:].isdigit())
        ]

        return True, source_nodes, sink_nodes

def find_terminal_nodes(
    network_dataframe: pd.DataFrame,
    return_type: str = 'both',
    logger: Optional[BioMathForgeLogger] = None
) -> Tuple[List[str], List[str]]:
    """
    Identify source and sink nodes from the network.

    Args:
        network_dataframe: pd.DataFrame with 'from' and 'to' columns.
        return_type: One of 'both', 'source', 'sink', or 'terminal'.
        logger: Optional logger.

    Returns:
        List(s) of source and/or sink nodes.
    """
    logger = logger or BioMathForgeLogger("network_terminal")
    G = nx.from_pandas_edgelist(network_dataframe, 'from', 'to', create_using=nx.DiGraph())

    # Clean dummy nodes
    dummy_nodes = [
        node for node in G.nodes()
        if isinstance(node, str) and node.startswith('r') and node[1:].isdigit()
        and (G.in_degree(node) == 0 or G.out_degree(node) == 0)
    ]
    G.remove_nodes_from(dummy_nodes)

    source_nodes = [
        node for node in G.nodes()
        if G.in_degree(node) == 0 and not (isinstance(node, str) and node.startswith('r') and node[1:].isdigit())
    ]
    sink_nodes = [
        node for node in G.nodes()
        if G.out_degree(node) == 0 and not (isinstance(node, str) and node.startswith('r') and node[1:].isdigit())
    ]

    if return_type == 'source':
        return source_nodes
    elif return_type == 'sink':
        return sink_nodes
    elif return_type == 'terminal':
        return list(set(source_nodes + sink_nodes))
    elif return_type == 'both':
        return source_nodes, sink_nodes
    else:
        raise ValueError("return_type must be one of: 'both', 'source', 'sink', 'terminal'")
