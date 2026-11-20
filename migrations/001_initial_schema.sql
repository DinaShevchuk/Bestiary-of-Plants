-- Initial database schema migration

CREATE TABLE sources (
  source_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_key TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  publisher TEXT,
  source_url TEXT,
  license_note TEXT,
  accessed_at TEXT,
  notes TEXT
, title_ru TEXT, notes_ru TEXT);

CREATE TABLE plants (
  plant_id INTEGER PRIMARY KEY AUTOINCREMENT,
  gbif_taxon_key INTEGER UNIQUE,
  scientific_name TEXT NOT NULL,
  scientific_name_authorship TEXT,
  family TEXT,
  genus TEXT,
  specific_epithet TEXT,
  taxonomic_status TEXT,
  kingdom TEXT DEFAULT 'Plantae',
  rank TEXT,
  description TEXT,
  description_language TEXT,
  description_source_id INTEGER REFERENCES sources(source_id),
  is_medicinal INTEGER NOT NULL DEFAULT 0 CHECK (is_medicinal IN (0,1)),
  data_status TEXT NOT NULL DEFAULT 'taxonomy_only',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
, family_ru TEXT, name_ru TEXT, name_ru_status TEXT, description_ru TEXT);

CREATE TABLE plant_names (
  plant_name_id INTEGER PRIMARY KEY AUTOINCREMENT,
  plant_id INTEGER NOT NULL REFERENCES plants(plant_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  language TEXT,
  name_type TEXT NOT NULL DEFAULT 'common',
  source_id INTEGER REFERENCES sources(source_id), name_ru TEXT, ru_status TEXT,
  UNIQUE(plant_id, name, language, name_type)
);

CREATE TABLE categories (
  category_id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  name_ru TEXT NOT NULL,
  name_en TEXT,
  description TEXT
);

CREATE TABLE plant_categories (
  plant_id INTEGER NOT NULL REFERENCES plants(plant_id) ON DELETE CASCADE,
  category_id INTEGER NOT NULL REFERENCES categories(category_id) ON DELETE CASCADE,
  assignment_source_id INTEGER REFERENCES sources(source_id),
  evidence_note TEXT,
  PRIMARY KEY (plant_id, category_id)
);

CREATE TABLE plant_descriptions (
  description_id INTEGER PRIMARY KEY AUTOINCREMENT,
  plant_id INTEGER NOT NULL REFERENCES plants(plant_id) ON DELETE CASCADE,
  section TEXT NOT NULL,
  content TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'ru',
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  source_reference TEXT,
  evidence_level TEXT NOT NULL DEFAULT 'source_reported',
  UNIQUE(plant_id, section, language, source_id, source_reference)
);

CREATE TABLE compounds (
  compound_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  normalized_name TEXT NOT NULL,
  cas_number TEXT, name_ru TEXT, name_ru_status TEXT,
  UNIQUE(normalized_name)
);

CREATE TABLE plant_compounds (
  plant_id INTEGER NOT NULL REFERENCES plants(plant_id) ON DELETE CASCADE,
  compound_id INTEGER NOT NULL REFERENCES compounds(compound_id) ON DELETE CASCADE,
  plant_part TEXT,
  concentration_low_ppm REAL,
  concentration_high_ppm REAL,
  compound_class TEXT,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  source_reference TEXT, plant_part_ru TEXT, compound_class_ru TEXT,
  PRIMARY KEY (plant_id, compound_id, plant_part, source_id)
);

CREATE TABLE habitats (
  habitat_id INTEGER PRIMARY KEY AUTOINCREMENT,
  plant_id INTEGER NOT NULL REFERENCES plants(plant_id) ON DELETE CASCADE,
  locality TEXT,
  country_code TEXT,
  habitat_description TEXT,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  source_reference TEXT
);

CREATE TABLE plant_images (
  image_id INTEGER PRIMARY KEY AUTOINCREMENT,
  plant_id INTEGER NOT NULL REFERENCES plants(plant_id) ON DELETE CASCADE,
  image_url TEXT NOT NULL,
  creator TEXT,
  license_note TEXT,
  source_id INTEGER REFERENCES sources(source_id),
  is_verified INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0,1))
);

CREATE TABLE documents (
  document_id TEXT PRIMARY KEY,
  plant_id INTEGER REFERENCES plants(plant_id) ON DELETE CASCADE,
  plant_name TEXT,
  scientific_name TEXT,
  aliases_json TEXT NOT NULL DEFAULT '[]',
  categories_json TEXT NOT NULL DEFAULT '[]',
  content TEXT NOT NULL,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  source_title TEXT NOT NULL,
  source_url TEXT,
  publisher TEXT,
  published_at TEXT,
  accessed_at TEXT,
  language TEXT NOT NULL DEFAULT 'en',
  license_or_usage_note TEXT,
  parent_document_id TEXT REFERENCES documents(document_id),
  chunk_index INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE import_batches (
  batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_key TEXT NOT NULL,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT,
  imported_rows INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'started',
  details TEXT
);

CREATE TABLE 'documents_fts_data'(id INTEGER PRIMARY KEY, block BLOB);

CREATE TABLE 'documents_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;

CREATE TABLE 'documents_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3, c4, c5, c6);

CREATE TABLE 'documents_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);

CREATE TABLE 'documents_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;

CREATE TABLE plant_uses (
  plant_use_id INTEGER PRIMARY KEY AUTOINCREMENT,
  plant_id INTEGER NOT NULL REFERENCES plants(plant_id) ON DELETE CASCADE,
  use_text TEXT NOT NULL,
  use_type TEXT,
  evidence_type TEXT NOT NULL,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  source_reference TEXT
, use_text_ru TEXT, activity_en TEXT, activity_ru TEXT, local_name TEXT, country_en TEXT, country_ru TEXT, ru_status TEXT);

CREATE TABLE families_ru(family TEXT PRIMARY KEY, name_ru TEXT NOT NULL, plant_count INTEGER);

CREATE TABLE documents_ru(
 document_id TEXT PRIMARY KEY, original_document_id TEXT REFERENCES documents(document_id),
 plant_id INTEGER REFERENCES plants(plant_id) ON DELETE CASCADE,
 plant_name_ru TEXT, scientific_name TEXT, family_ru TEXT,
 aliases_json TEXT NOT NULL DEFAULT '[]', categories_json TEXT NOT NULL DEFAULT '[]', categories_ru TEXT,
 content TEXT NOT NULL, source_id INTEGER NOT NULL REFERENCES sources(source_id),
 source_title TEXT NOT NULL, source_url TEXT, publisher TEXT, accessed_at TEXT,
 language TEXT NOT NULL DEFAULT 'ru', license_or_usage_note TEXT,
 translation_note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE 'documents_ru_fts_data'(id INTEGER PRIMARY KEY, block BLOB);

CREATE TABLE 'documents_ru_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;

CREATE TABLE 'documents_ru_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3, c4, c5, c6);

CREATE TABLE 'documents_ru_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);

CREATE TABLE 'documents_ru_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;

CREATE TABLE translation_info(key TEXT PRIMARY KEY, value TEXT);

CREATE VIRTUAL TABLE documents_fts USING fts5(
  document_id UNINDEXED,
  plant_name,
  scientific_name,
  aliases,
  categories,
  content,
  source_title,
  tokenize = 'unicode61 remove_diacritics 2'
);

CREATE VIRTUAL TABLE documents_ru_fts using fts5(
 document_id UNINDEXED, plant_name, scientific_name, aliases, categories, content, source_title,
 tokenize='unicode61 remove_diacritics 2');

CREATE VIRTUAL TABLE plants_fts
        USING fts5(
            plant_name_ru,
            scientific_name,
            family_ru,
            categories_ru,
            description_ru,
            medicinal_properties_ru,
            safety_ru,
            content='plants',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );

CREATE TABLE 'plants_fts_data'(id INTEGER PRIMARY KEY, block BLOB);

CREATE TABLE 'plants_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;

CREATE TABLE 'plants_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);

CREATE TABLE 'plants_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;

CREATE INDEX idx_plants_scientific_name ON plants(scientific_name);

CREATE INDEX idx_plants_family ON plants(family);

CREATE INDEX idx_plant_names_name ON plant_names(name);

CREATE INDEX idx_documents_plant_id ON documents(plant_id);

CREATE INDEX idx_documents_source_id ON documents(source_id);

CREATE INDEX idx_plant_compounds_plant_id ON plant_compounds(plant_id);

CREATE INDEX idx_plant_categories_category_id ON plant_categories(category_id);

CREATE UNIQUE INDEX idx_plants_scientific_name_unique ON plants(scientific_name COLLATE NOCASE);

CREATE INDEX idx_documents_ru_plant on documents_ru(plant_id);

CREATE TRIGGER documents_fts_ai AFTER INSERT ON documents BEGIN
  INSERT INTO documents_fts(document_id,plant_name,scientific_name,aliases,categories,content,source_title)
  VALUES (new.document_id, COALESCE(new.plant_name,''), COALESCE(new.scientific_name,''), new.aliases_json, new.categories_json, new.content, new.source_title);
END;

CREATE TRIGGER documents_fts_ad AFTER DELETE ON documents BEGIN
  DELETE FROM documents_fts WHERE document_id = old.document_id;
END;

CREATE TRIGGER documents_fts_au AFTER UPDATE ON documents BEGIN
  DELETE FROM documents_fts WHERE document_id = old.document_id;
  INSERT INTO documents_fts(document_id,plant_name,scientific_name,aliases,categories,content,source_title)
  VALUES (new.document_id, COALESCE(new.plant_name,''), COALESCE(new.scientific_name,''), new.aliases_json, new.categories_json, new.content, new.source_title);
END;

