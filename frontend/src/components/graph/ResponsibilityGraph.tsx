import type {
  GraphEdge,
  GraphNode,
  GraphResolveResponse,
} from "../../api/graphTypes";

interface ResponsibilityGraphProps {
  data: GraphResolveResponse;
}

/**
 * Simple CSS/SVG-free flow for the Responsibility Graph (P6).
 *
 * The chain Location → Jurisdiction → Authority → Department → Service → Issue
 * → Escalation is rendered as ordered node cards with labelled arrows so a
 * judge can read WHY an issue was routed the way it was. No graph library is
 * required: the layout is a plain flex row that wraps on narrow screens.
 */
export function ResponsibilityGraph({ data }: ResponsibilityGraphProps) {
  if (data.nodes.length === 0) {
    return <p className="muted">No responsibility chain could be built.</p>;
  }

  return (
    <div className="resp-graph">
      <div className="resp-graph-chain">
        {data.nodes.map((node, index) => {
          const next = data.nodes[index + 1];
          const edge = next
            ? data.edges.find((e) => e.source === node.id && e.target === next.id)
            : undefined;
          return (
            <div key={node.id} className="resp-graph-step">
              <GraphNodeCard node={node} />
              {edge && next && index < data.nodes.length - 1 && (
                <GraphArrow edge={edge} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function GraphNodeCard({ node }: { node: GraphNode }) {
  return (
    <div className={`resp-graph-node resp-graph-node-${node.type.toLowerCase()}`}>
      <span className="resp-graph-node-type">{node.type}</span>
      <span className="resp-graph-node-label" title={node.label}>
        {node.label}
      </span>
    </div>
  );
}

function GraphArrow({ edge }: { edge: GraphEdge }) {
  return (
    <div className="resp-graph-arrow" title={edge.label ?? edge.type}>
      <span className="resp-graph-arrow-line" aria-hidden="true" />
      <span className="resp-graph-arrow-type">{edge.type}</span>
    </div>
  );
}