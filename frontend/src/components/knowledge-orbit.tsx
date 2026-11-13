import { BrandMark } from "./brand";
export function KnowledgeOrbit() {
  return (
    <div className="knowledge-orbit" aria-hidden="true">
      <div className="orbit-grid" />
      <div className="orbit-ring ring-outer" />
      <div className="orbit-ring ring-middle" />
      <div className="orbit-ring ring-inner" />
      <div className="orbit-line line-one" />
      <div className="orbit-line line-two" />
      <div className="orbit-line line-three" />
      <div className="orbit-center">
        <BrandMark />
        <span>CYBERSAGE</span>
      </div>
      <div className="orbit-node node-one">
        <span className="node-light" />
        POLICY<span>01</span>
      </div>
      <div className="orbit-node node-two">
        <span className="node-light blue" />
        FRAMEWORK<span>02</span>
      </div>
      <div className="orbit-node node-three">
        <span className="node-light sand" />
        CASEBOOK<span>03</span>
      </div>
      <span className="orbit-caption">
        CONNECTED KNOWLEDGE. GROUNDED ANSWERS.
      </span>
    </div>
  );
}
