import sqlite3
from pathlib import Path
import json

SCHEMA_VERSION = 3

def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
      CREATE TABLE IF NOT EXISTS meta(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      );
    """)
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version';").fetchone()
    if row is None:
        conn.execute("INSERT INTO meta(key,value) VALUES('schema_version', ?);", (str(SCHEMA_VERSION),))
    conn.commit()

    conn.execute("""
      CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        source_type TEXT NOT NULL,
        title TEXT,
        doi TEXT,
        year INTEGER,
        path TEXT NOT NULL,
        bundle_path TEXT NOT NULL,
        created_at TEXT NOT NULL
      );
    """)

    conn.execute("""
      CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        input_dir TEXT NOT NULL,
        output_dir TEXT NOT NULL,
        primary_model TEXT NOT NULL,
        auditor_model TEXT NOT NULL,
        gap_model TEXT NOT NULL,
        status TEXT NOT NULL,
        notes TEXT
      );
    """)

    conn.execute("""
      CREATE TABLE IF NOT EXISTS molecules (
        molecule_id TEXT PRIMARY KEY,
        name_as_written TEXT,
        normalized_name TEXT,
        smiles TEXT,
        inchi_key TEXT,
        total_nitrogen_count INTEGER,
        quaternary_n_count INTEGER,
        formal_charge INTEGER,
        head_group_class TEXT,
        chain_lengths TEXT,
        created_at TEXT NOT NULL
      );
    """)

    conn.execute("""
      CREATE TABLE IF NOT EXISTS experiments (
        experiment_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        organism TEXT,
        strain TEXT,
        assay_type TEXT,
        conditions TEXT,
        exposure_protocol TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
      );
    """)

    conn.execute("""
      CREATE TABLE IF NOT EXISTS results (
        result_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        experiment_id TEXT NOT NULL,
        molecule_id TEXT,
        endpoint TEXT,
        value REAL,
        units TEXT,
        directionality TEXT,
        confidence REAL,
        evidence_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
        FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
        FOREIGN KEY(molecule_id) REFERENCES molecules(molecule_id) ON DELETE CASCADE
      );
    """)

    conn.execute("""
      CREATE TABLE IF NOT EXISTS evidence (
        evidence_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        page INTEGER,
        table_id TEXT,
        cell TEXT,
        snippet TEXT,
        source_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
      );
    """)

    conn.execute("""
      CREATE TABLE IF NOT EXISTS audits (
        audit_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        model TEXT NOT NULL,
        verdict TEXT NOT NULL,
        confidence REAL NOT NULL,
        issues_json TEXT,
        suggested_fix_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
      );
    """)

    conn.execute("""
      CREATE TABLE IF NOT EXISTS gap_suggestions (
        suggestion_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        model TEXT NOT NULL,
        kind TEXT NOT NULL,
        page INTEGER,
        description TEXT NOT NULL,
        rationale TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
      );
    """)

    conn.execute("""
      CREATE TABLE IF NOT EXISTS repairs (
        repair_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        model TEXT NOT NULL,
        reason TEXT NOT NULL,
        before_json TEXT NOT NULL,
        after_json TEXT NOT NULL,
        applied INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
      );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_year ON documents(year);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mol_inchi ON molecules(inchi_key);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_res_doc ON results(doc_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_res_mol ON results(molecule_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_exp_doc ON experiments(doc_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_doc ON audits(doc_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_entity ON audits(entity_type, entity_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gaps_doc ON gap_suggestions(doc_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_repairs_doc ON repairs(doc_id);")
    conn.commit()

def insert_run(conn, run: dict) -> None:
    conn.execute("""
      INSERT INTO runs(run_id,started_at,finished_at,input_dir,output_dir,primary_model,auditor_model,gap_model,status,notes)
      VALUES (?,?,?,?,?,?,?,?,?,?);
    """, (
        run["run_id"], run["started_at"], run.get("finished_at"),
        run["input_dir"], run["output_dir"],
        run["primary_model"], run["auditor_model"], run["gap_model"],
        run["status"], run.get("notes"),
    ))
    conn.commit()

def insert_document(conn, doc: dict) -> None:
    conn.execute("""
      INSERT OR IGNORE INTO documents(doc_id,source_type,title,doi,year,path,bundle_path,created_at)
      VALUES (?,?,?,?,?,?,?,?);
    """, (
        doc["doc_id"], doc.get("source_type","paper"), doc.get("title"), doc.get("doi"), doc.get("year"),
        doc["path"], doc["bundle_path"], doc["created_at"]
    ))
    conn.commit()

def insert_evidence(conn, doc_id: str, ev: dict) -> str:
    import uuid
    from datetime import datetime, timezone
    evidence_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    conn.execute("""
      INSERT INTO evidence(evidence_id,doc_id,kind,page,table_id,cell,snippet,source_json,created_at)
      VALUES (?,?,?,?,?,?,?,?,?);
    """, (
        evidence_id, doc_id, ev.get("kind","snippet"), ev.get("page"),
        ev.get("table_id"), ev.get("cell"), ev.get("snippet"),
        json.dumps(ev.get("source_json")) if isinstance(ev.get("source_json"), (dict,list)) else ev.get("source_json"),
        created_at
    ))
    conn.commit()
    return evidence_id

def insert_molecule(conn, doc_id: str, mol: dict) -> None:
    from datetime import datetime, timezone
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    conn.execute("""
      INSERT OR IGNORE INTO molecules(
        molecule_id,name_as_written,normalized_name,smiles,inchi_key,total_nitrogen_count,quaternary_n_count,formal_charge,head_group_class,chain_lengths,created_at
      ) VALUES (?,?,?,?,?,?,?,?,?,?,?);
    """, (
        mol["molecule_id"], mol.get("name_as_written"), mol.get("normalized_name"),
        mol.get("smiles"), mol.get("inchi_key"),
        mol.get("total_nitrogen_count"), mol.get("quaternary_n_count"), mol.get("formal_charge"),
        mol.get("head_group_class"),
        json.dumps(mol.get("chain_lengths")) if mol.get("chain_lengths") is not None else None,
        created_at
    ))
    conn.commit()

def insert_experiment(conn, doc_id: str, exp: dict) -> None:
    from datetime import datetime, timezone
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    conn.execute("""
      INSERT OR IGNORE INTO experiments(experiment_id,doc_id,organism,strain,assay_type,conditions,exposure_protocol,created_at)
      VALUES (?,?,?,?,?,?,?,?);
    """, (
        exp["experiment_id"], doc_id, exp.get("organism"), exp.get("strain"), exp.get("assay_type"),
        json.dumps(exp.get("conditions")) if exp.get("conditions") is not None else None,
        json.dumps(exp.get("exposure_protocol")) if exp.get("exposure_protocol") is not None else None,
        created_at
    ))
    conn.commit()

def insert_result(conn, doc_id: str, res: dict) -> None:
    from datetime import datetime, timezone
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    conn.execute("""
      INSERT OR IGNORE INTO results(result_id,doc_id,experiment_id,molecule_id,endpoint,value,units,directionality,confidence,evidence_json,created_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?);
    """, (
        res["result_id"], doc_id, res["experiment_id"], res.get("molecule_id"),
        res.get("endpoint"), res.get("value"), res.get("units"),
        res.get("directionality"), float(res.get("confidence",0.0)),
        json.dumps(res.get("evidence") or {}),
        created_at
    ))
    conn.commit()

def update_molecule(conn, mol: dict) -> None:
    conn.execute("""
      UPDATE molecules
      SET name_as_written=?, normalized_name=?, smiles=?, head_group_class=?, chain_lengths=?
      WHERE molecule_id=?;
    """, (
        mol.get("name_as_written"), mol.get("normalized_name"), mol.get("smiles"),
        mol.get("head_group_class"),
        json.dumps(mol.get("chain_lengths")) if mol.get("chain_lengths") is not None else None,
        mol["molecule_id"]
    ))
    conn.commit()

def update_experiment(conn, doc_id: str, exp: dict) -> None:
    conn.execute("""
      UPDATE experiments
      SET organism=?, strain=?, assay_type=?, conditions=?, exposure_protocol=?
      WHERE experiment_id=? AND doc_id=?;
    """, (
        exp.get("organism"), exp.get("strain"), exp.get("assay_type"),
        json.dumps(exp.get("conditions")) if exp.get("conditions") is not None else None,
        json.dumps(exp.get("exposure_protocol")) if exp.get("exposure_protocol") is not None else None,
        exp["experiment_id"], doc_id
    ))
    conn.commit()

def update_result(conn, doc_id: str, res: dict) -> None:
    conn.execute("""
      UPDATE results
      SET experiment_id=?, molecule_id=?, endpoint=?, value=?, units=?, directionality=?, confidence=?, evidence_json=?
      WHERE result_id=? AND doc_id=?;
    """, (
        res.get("experiment_id"), res.get("molecule_id"), res.get("endpoint"),
        res.get("value"), res.get("units"), res.get("directionality"),
        float(res.get("confidence",0.0)),
        json.dumps(res.get("evidence") or {}),
        res["result_id"], doc_id
    ))
    conn.commit()

def insert_audit(conn, row: dict) -> None:
    conn.execute("""
      INSERT OR REPLACE INTO audits(audit_id,doc_id,entity_type,entity_id,model,verdict,confidence,issues_json,suggested_fix_json,created_at)
      VALUES (?,?,?,?,?,?,?,?,?,?);
    """, (
        row["audit_id"], row["doc_id"], row["entity_type"], row["entity_id"], row["model"],
        row["verdict"], float(row["confidence"]),
        row.get("issues_json"), row.get("suggested_fix_json"), row["created_at"]
    ))
    conn.commit()

def insert_gap(conn, row: dict) -> None:
    conn.execute("""
      INSERT OR REPLACE INTO gap_suggestions(suggestion_id,doc_id,model,kind,page,description,rationale,created_at)
      VALUES (?,?,?,?,?,?,?,?);
    """, (
        row["suggestion_id"], row["doc_id"], row["model"], row["kind"],
        row.get("page"), row["description"], row.get("rationale"), row["created_at"]
    ))
    conn.commit()

def insert_repair(conn, row: dict) -> None:
    conn.execute("""
      INSERT OR REPLACE INTO repairs(repair_id,doc_id,entity_type,entity_id,model,reason,before_json,after_json,applied,created_at)
      VALUES (?,?,?,?,?,?,?,?,?,?);
    """, (
        row["repair_id"], row["doc_id"], row["entity_type"], row["entity_id"], row["model"],
        row["reason"], row["before_json"], row["after_json"], int(row["applied"]), row["created_at"]
    ))
    conn.commit()
