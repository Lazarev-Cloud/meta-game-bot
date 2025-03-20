CREATE TABLE IF NOT EXISTS player_locations (
    player_id INTEGER NOT NULL,
    district_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (district_id) REFERENCES districts(district_id)
); 