CREATE TABLE IF NOT EXISTS spirits (
    number TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    attributes TEXT NOT NULL DEFAULT '[]',
    stats_total INTEGER,
    hp INTEGER,
    physical_attack INTEGER,
    magic_attack INTEGER,
    physical_defense INTEGER,
    magic_defense INTEGER,
    speed INTEGER,
    skills TEXT NOT NULL DEFAULT '[]',
    bloodline_skills TEXT NOT NULL DEFAULT '[]',
    skill_stone_skills TEXT NOT NULL DEFAULT '[]',
    evolution_chain TEXT,
    obtain_method TEXT,
    trait_name TEXT,
    trait_description TEXT,
    image_url TEXT,
    source_url TEXT NOT NULL,
    source_updated_at TEXT,
    scraped_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_spirits_name ON spirits(name);
CREATE INDEX IF NOT EXISTS idx_spirits_attributes ON spirits(attributes);
