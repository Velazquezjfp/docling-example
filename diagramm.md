flowchart TB
  %% ============ inputs ============
  PDF[/"📄 PDF manual<br/>Betriebshandbuch_ZSD.pdf"/]
  ONTO[/"📐 ontology.yaml<br/>26 classes · 32 relations<br/>(ConfigMap, mounted read-only)"/]
  USER(["👤 User in browser"])
  ING["Ingress + IAM (PGA)<br/>injects X-Forwarded-User / -Email / -Groups"]

  %% ============ platform endpoints ============
  subgraph EXT["Platform model endpoints (OpenAI-compatible, not ours)"]
    direction LR
    LLM["🧠 LLM · gemma4<br/>/v1/chat/completions<br/>streaming + JSON schema"]
    EMB["🔢 Embedding · multilingual-e5-large<br/>/v1/embeddings · 1024 dim"]
    VLM["🖼 VLM (optional, off)"]
  end

  %% ============ dgs ============
  subgraph DGS["📦 Container dgs · docling_graph_service · POST /v1/process · :8080"]
    direction TB
    G1["① Convert<br/>docling: layout · TableFormer · OCR de/en"]
    G2["② Clean up DoclingDocument<br/>page furniture · headings · captions"]
    G3["③a Chunk for search<br/>HybridChunker · 512 tokens<br/>tables kept whole"]
    G4["④a Embed chunks<br/>prefix 'passage: ' · batches of 64"]
    G5["③b Extract graph<br/>slices → LLM, output forced into<br/>JSON schema compiled from ontology"]
    G6["④b Deduplicate<br/>ontology identity rules"]
    G7["⑤ materialize()<br/>join on item ids texts/40, tables/11 …<br/>node → chunk_ids · edge → chunk_ids"]
    G8["⑥ Write run directory"]
    G1 --> G2
    G2 --> G3
    G3 --> G4
    G4 --> G7
    G2 --> G5
    G5 --> G6
    G6 --> G7
    G7 --> G8
  end

  VOL[("🗂 Shared volume (RWX)<br/>run directory per manual<br/>response.json · markdown")]

  %% ============ indexer ============
  subgraph OSI["📦 Container indexer · osi ingest · one-shot, exits in seconds"]
    direction TB
    I1["① Load response.json<br/>check vector dim = 1024, no zero vectors"]
    I2["② Take the lease<br/>manifest status → indexing"]
    I3["③ Transform<br/>stamp reverse links chunk → nodes/edges<br/>extract identifiers by ontology regex"]
    I4["④ Bulk write · deterministic _id<br/>(re-run = upsert)"]
    I5["⑤ Verify counts · sweep the old run"]
    I6["⑥ Release<br/>manifest status → active"]
    I1 --> I2
    I2 --> I3
    I3 --> I4
    I4 --> I5
    I5 --> I6
  end

  %% ============ opensearch ============
  subgraph OS["🗄 OpenSearch ≥ 2.19 · k-NN plugin · the only data store"]
    direction LR
    XC[("bhb-chunks<br/>text + 1024-dim vector<br/>+ links to graph")]
    XN[("bhb-nodes<br/>one record per entity")]
    XD[("bhb-documents<br/>one per manual<br/>+ whole graph JSON blob")]
    XM[("bhb-manifest<br/>ingest state + lock")]
  end

  %% ============ chat ============
  subgraph CHAT["📦 Container chat · Streamlit :8501 · 1 replica"]
    direction TB
    CU["rag_users<br/>headers → user + groups → policy<br/>quota · allowed manuals"]
    CS["chat_system<br/>UI · conversations · daily quota"]
    CR["rag_retrieval<br/>4 search channels + 1-hop graph<br/>→ prompt with citations"]
    CG["in-memory union graph<br/>+ label index"]
    SQL[("SQLite on PVC<br/>conversations · messages · counters")]
    CU --> CS
    CS --> CR
    CS <--> SQL
    CR --- CG
  end

  %% ============ ingest wiring ============
  PDF -->|"multipart upload"| G1
  ONTO -->|"schema + identity rules"| G5
  G1 -.->|"figure images"| VLM
  G4 <-->|"chunk texts → vectors"| EMB
  G5 <-->|"slice + schema → typed JSON"| LLM
  G8 --> VOL
  VOL -->|"read"| I1
  ONTO -->|"identifier regexes, root systems"| I3
  I2 --> XM
  I4 --> XC
  I4 --> XN
  I4 --> XD
  I6 --> XM

  %% ============ ask wiring (details in RETRIEVAL-FLOW.md) ============
  USER --> ING
  ING -->|"HTTP + identity headers"| CU
  XD -->|"graph blobs at start-up"| CG
  XD -->|"document list · cached 5 min"| CS
  CR <-->|"msearch (4 channels) · mget"| XC
  CR <-->|"question → 1 vector, 'query: '"| EMB
  CR <-->|"prompt → streamed answer"| LLM
  CS -->|"answer + citations"| USER

  %% ============ data bubbles ============
  B0("💬 <b>ontology.yaml → schema</b><br/>RESPONSIBLE_FOR:<br/>  source: Person · target: NodeBase<br/>  label_de: 'verantwortlich für'<br/>  cues_de: ['zuständig', …]")
  B1("💬 <b>response.json</b> (dgs output)<br/>{ document: {name, sha256, pages: 29},<br/>  chunks: [112 × {chunk_id, text, embedding[1024]}],<br/>  graph: {nodes: [250], edges: [154]},<br/>  degraded: {vlm, embeddings, graph: false} }")
  B2("💬 <b>bhb-chunks</b> _id 2bb722f565a0-0055<br/>kind: table · page_numbers: [17]<br/>caption: 'Tabelle 7: Standard Operating Procedures'<br/>text: '| SOP-ZSD-06 | Kaltstart … | Kai Ostermann |'<br/>embedding: [0.0019, 0.0003, -0.0570, … ×1024]<br/>identifiers: ['SOP-ZSD-01' … 'SOP-CAAS-06']<br/>node_labels: ['kai ostermann', 'sop-zsd-06', …] (14)<br/>edge_ids: ['2aca7dfa9b3a135b', …] (7)")
  B3("💬 <b>bhb-nodes</b> _id 2bb722f565a0:Person_c148…<br/>type: Person · label: 'Kai Ostermann'<br/>attributes: {role_title: 'Verantwortlicher ZSD, IAM-Betrieb',<br/>  phone_ext: '1315', org_unit: 'Bereich IT-S 1'}<br/>chunk_ids: ['…-0001', '…-0002', '…-0003'] · pages: [1, 2]")
  B4("💬 <b>bhb-documents</b> _id BHB-PLT-0007<br/>title: 'Betriebshandbuch ZSD - …' · version: '2.3'<br/>root_system: 'Zentrale Sicherheitsdienste'<br/>counts: {chunks: 112, nodes: 250, edges: 154}<br/>graph.edges[i]: {id: '2aca7dfa9b3a135b',<br/>  source: Kai Ostermann, type: RESPONSIBLE_FOR,<br/>  target: SOP-ZSD-06, polarity: positive,<br/>  properties: {raci: 'verantwortlich'},<br/>  quote: 'SOP-ZSD-06 | Kaltstart … | Kai Ostermann',<br/>  provenance: {pages: [17], chunk_ids: ['…-0055']}}")
  B5("💬 <b>bhb-manifest</b> _id BHB-PLT-0007<br/>status: indexing → active<br/>run_id, doc_sha256, owner, started_at, finished_at<br/>counts · swept · embedding_model · history[]")

  ONTO -.- B0
  VOL -.- B1
  XC -.- B2
  XN -.- B3
  XD -.- B4
  XM -.- B5

  classDef container fill:#eef4ff,stroke:#3b6fd8,stroke-width:2px
  classDef store fill:#fff7e6,stroke:#d08a00
  classDef ext fill:#f3f3f3,stroke:#888,stroke-dasharray:4 3
  classDef bubble fill:#fffde7,stroke:#b9a100,stroke-dasharray:3 3,font-family:monospace,font-size:11px,text-align:left
  class DGS,OSI,CHAT container
  class OS,VOL store
  class EXT ext
  class B0,B1,B2,B3,B4,B5 bubble
