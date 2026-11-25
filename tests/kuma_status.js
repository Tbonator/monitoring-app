// Read-only report of Uptime Kuma monitors and their latest heartbeats.
// Runs INSIDE the uptime-kuma container (uses its bundled sqlite3 driver):
//   docker exec -i uptime-kuma node - < tests/kuma_status.js
const sqlite3 = require("/app/node_modules/@louislam/sqlite3");
const db = new sqlite3.Database("/app/data/kuma.db", sqlite3.OPEN_READONLY);
const sql = `
  SELECT m.id, m.name, m.type, m.url, m.interval, m.maxretries, m.active,
         (SELECT COUNT(*) FROM heartbeat h WHERE h.monitor_id = m.id) AS beats,
         (SELECT h.status || ' @ ' || h.time FROM heartbeat h
            WHERE h.monitor_id = m.id ORDER BY h.time DESC LIMIT 1) AS latest,
         (SELECT group_concat(s, '') FROM (SELECT CASE h.status WHEN 1 THEN 'U' WHEN 0 THEN 'D' WHEN 2 THEN 'P' ELSE '?' END AS s
            FROM heartbeat h WHERE h.monitor_id = m.id ORDER BY h.time DESC LIMIT 12)) AS recent
  FROM monitor m ORDER BY m.id`;
db.all(sql, (err, rows) => {
  if (err) { console.error(err.message); process.exit(1); }
  for (const r of rows) {
    console.log(`#${r.id} ${r.name} [${r.type}] active=${r.active} interval=${r.interval}s retries=${r.maxretries}`);
    console.log(`   ${r.url}`);
    console.log(`   heartbeats=${r.beats} latest(status 1=up 0=down 2=pending)=${r.latest} recent(newest first)=${r.recent}`);
  }
  db.close();
});
