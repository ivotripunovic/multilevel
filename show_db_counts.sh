DB=db.sqlite3
sqlite3 $DB "SELECT name FROM sqlite_master WHERE type='table';" | while read tbl; do
  echo "$tbl, rows: $(sqlite3 $DB  "SELECT COUNT(*) FROM $tbl;")"
done
